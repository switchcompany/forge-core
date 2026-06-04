"""Forge Core CLI — powered by typer."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from forge_core import __version__

app = typer.Typer(
    name="forge-core",
    help="AI-powered backend test generation engine",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    project_path: Path = typer.Argument(
        ".",
        help="Path to the backend project to test",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    target_coverage: float = typer.Option(
        90.0, "--target", "-t", help="Target line coverage percentage"
    ),
    max_iterations: int = typer.Option(
        10, "--max-iterations", "-i", help="Maximum generation iterations"
    ),
    model: str = typer.Option(
        "", "--model", "-m", help="AI model to use (e.g., gpt-4o, claude-sonnet-4-20250514)"
    ),
    provider: str = typer.Option(
        "", "--provider", "-p", help="AI provider (openai, anthropic, ollama, azure)"
    ),
    api_key: str = typer.Option(
        "", "--api-key", "-k", help="AI provider API key (or set OPENAI_API_KEY env var)"
    ),
    mode: str = typer.Option(
        "full", "--mode", help="Run mode: full, targeted, analyze_only, analyze_review"
    ),
    files: Optional[list[str]] = typer.Option(
        None, "--file", "-f", help="Specific files to test (targeted mode)"
    ),
    incremental: bool = typer.Option(
        False, "--incremental/--no-incremental",
        help="Only analyze files changed since last run (CI mode, ~4x cheaper)"
    ),
):
    """Run Forge Core on a backend project to generate unit tests."""
    from forge_core.auth import load_auth_token, verify_license
    from forge_core.config import load_config
    from forge_core.models.config import RunMode
    from forge_core.orchestrator import Orchestrator
    from forge_core.utils import logger
    from forge_core.utils.reporter import upload_report

    project_path = project_path.resolve()

    auth_token = load_auth_token()
    config = load_config(
        project_path=project_path,
        api_key=api_key,
        provider=provider,
        model=model,
        target_coverage=target_coverage,
        auth_token=auth_token,
    )
    config.max_iterations = max_iterations
    config.incremental = incremental

    try:
        config.mode = RunMode(mode)
    except ValueError:
        logger.error(f"Invalid mode: {mode}. Use: full, targeted, analyze_only, analyze_review")
        raise typer.Exit(1)

    if files:
        config.mode = RunMode.TARGETED
        config.target_files = list(files)

    config = verify_license(config)

    # Validate API key — skip if using SaaS proxy (auth_token handles it)
    if not config.ai.api_key and not config.auth_token:
        console.print(
            "[red]No API key or auth token found.[/red]\n\n"
            "Set one of:\n"
            "  export SWITCHFORGE_TOKEN=fc_...  (SaaS proxy — recommended)\n"
            "  export OPENAI_API_KEY=sk-...\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  forge-core login --token YOUR_TOKEN\n"
        )
        raise typer.Exit(1)

    orchestrator = Orchestrator(config)
    report = orchestrator.run()

    if config.auth_token:
        import dataclasses

        asyncio.run(upload_report(config, dataclasses.asdict(report)))

    if report.production_files_changed > 0:
        logger.error("SAFETY VIOLATION: Production files were changed!")
        raise typer.Exit(2)

    raise typer.Exit(0)


@app.command()
def login(
    token: str = typer.Option(
        "", "--token", "-t", help="Auth token from theswitchcompany.online"
    ),
):
    """Authenticate with TheSwitchCompany SaaS for Pro/Enterprise features."""
    from forge_core.auth import save_auth_token, verify_license
    from forge_core.config import load_config
    from forge_core.utils import logger

    if not token:
        console.print(
            "Get your auth token from:\n"
            "  [blue]https://theswitchcompany.online/dashboard/settings[/blue]\n\n"
            "Then run:\n"
            "  forge-core login --token YOUR_TOKEN"
        )
        raise typer.Exit(0)

    save_auth_token(token)

    config = load_config(Path("."), auth_token=token)
    config = verify_license(config)
    logger.success(f"Logged in as {config.tenant.org_name or 'user'}")


@app.command()
def init(
    project_path: Path = typer.Argument(".", help="Path to the project"),
):
    """Initialize Forge Core in a project (creates .github/agent-config.yml)."""
    from forge_core.utils import logger

    project_path = project_path.resolve()
    config_dir = project_path / ".github"
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "agent-config.yml"
    if config_file.exists():
        logger.info("agent-config.yml already exists")
        raise typer.Exit(0)

    config_file.write_text(
        "# Forge Core configuration\n"
        "# See: https://theswitchcompany.online/docs/forge-core\n\n"
        "# Tenant (populated by SaaS or set manually)\n"
        'org_id: ""\n'
        'user_id: ""\n'
        'project_id: ""\n\n'
        "# Runtime\n"
        'runtime: "auto"\n'
        "max_parallel_agents: 4\n"
        'cache_dir: ".forge-cache"\n',
        encoding="utf-8",
    )

    logger.success(f"Initialized Forge Core in {project_path}")
    console.print("\nNext: [blue]forge-core run[/blue] to generate tests")


@app.command()
def version():
    """Show Forge Core version."""
    console.print(f"Forge Core v{__version__}")


@app.command()
def status():
    """Show current configuration and license status."""
    from forge_core.auth import load_auth_token, verify_license
    from forge_core.config import load_config

    auth_token = load_auth_token()
    config = load_config(Path("."), auth_token=auth_token)

    if auth_token:
        config = verify_license(config)

    console.print(f"\n[bold]Forge Core v{__version__}[/bold]\n")
    console.print(f"  Plan:     {config.limits.plan.value}")
    console.print(f"  Org:      {config.tenant.org_name or '(not set)'}")
    console.print(f"  Model:    {config.ai.model}")
    console.print(f"  Provider: {config.ai.provider.value}")
    console.print(f"  API Key:  {'***' + config.ai.api_key[-4:] if config.ai.api_key else '(not set)'}")
    console.print(f"  Auth:     {'✓ logged in' if auth_token else '✗ offline'}")
    console.print()


if __name__ == "__main__":
    app()
