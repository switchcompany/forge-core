"""Data models for configuration and tenant/plan data."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Plan(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    AUTO = "auto"


class RunMode(str, Enum):
    FULL = "full"
    TARGETED = "targeted"
    ANALYZE_ONLY = "analyze_only"
    ANALYZE_REVIEW = "analyze_review"


@dataclass
class TenantInfo:
    """Multi-tenant identification — populated by SaaS or CLI."""

    org_id: str = ""
    org_name: str = ""
    user_id: str = ""
    project_id: str = ""


@dataclass
class PlanLimits:
    """Usage limits per plan tier."""

    plan: Plan = Plan.FREE
    max_tests_per_month: int = 500
    max_repos: int = 1
    max_runs_per_month: int = 3
    max_concurrent_runs: int = 1
    ci_cd_enabled: bool = False
    cross_project_learning: bool = False
    max_parallel_agents: int = 2

    @classmethod
    def for_plan(cls, plan: Plan) -> "PlanLimits":
        if plan == Plan.PRO:
            return cls(
                plan=plan,
                max_tests_per_month=-1,
                max_repos=3,
                max_runs_per_month=50,
                max_concurrent_runs=5,
                ci_cd_enabled=True,
                cross_project_learning=True,
                max_parallel_agents=4,
            )
        elif plan == Plan.BUSINESS:
            return cls(
                plan=plan,
                max_tests_per_month=-1,
                max_repos=10,
                max_runs_per_month=200,
                max_concurrent_runs=10,
                ci_cd_enabled=True,
                cross_project_learning=True,
                max_parallel_agents=6,
            )
        elif plan == Plan.ENTERPRISE:
            return cls(
                plan=plan,
                max_tests_per_month=-1,
                max_repos=-1,
                max_runs_per_month=500,
                max_concurrent_runs=25,
                ci_cd_enabled=True,
                cross_project_learning=True,
                max_parallel_agents=8,
            )
        return cls()


@dataclass
class AIConfig:
    """AI provider configuration."""

    provider: AIProvider = AIProvider.AUTO
    model: str = "claude-sonnet-4-6"
    model_heavy: str = "claude-opus-4-8"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    use_saas_proxy: bool = False


@dataclass
class ForgeConfig:
    """Top-level engine configuration."""

    # Project
    project_path: Path = field(default_factory=lambda: Path("."))
    target_coverage: float = 90.0
    max_iterations: int = 10
    mode: RunMode = RunMode.FULL
    incremental: bool = False
    target_files: list[str] = field(default_factory=list)

    # AI
    ai: AIConfig = field(default_factory=AIConfig)

    # Tenant
    tenant: TenantInfo = field(default_factory=TenantInfo)

    # Plan
    limits: PlanLimits = field(default_factory=PlanLimits)

    # Engine
    central_agent_path: str = ""
    knowledge_packs_dir: str = "knowledge-packs"
    cache_dir: str = ".forge-cache"
    prompts_dir: str = ".github/prompts"

    # SaaS
    saas_api_url: str = "https://theswitchcompany.online"
    auth_token: str = ""
