from pathlib import Path
from forge_core.ai.prompts import load_prompt


def test_packaged_prompt_fallback():
    # Provide a non-existent project prompts dir so loader falls back to packaged prompts
    fake_dir = Path("/nonexistent/project/.github/prompts")
    content = load_prompt(fake_dir, "journey-mapping")
    assert content, "Expected packaged journey-mapping prompt to be returned as fallback"
    assert "Journey Mapping & DTO Registry" in content or "Purpose: Trace real user journeys" in content
