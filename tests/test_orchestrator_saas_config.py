from pathlib import Path

from forge_core.models.config import ForgeConfig
from forge_core.orchestrator import Orchestrator


def test_orchestrator_applies_saas_auth_to_ai_config(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.saas_api_url = "https://theswitchcompany.online/api/v1/ai"
    cfg.auth_token = "fc_testtoken"
    # ensure use_saas_proxy True
    cfg.ai.use_saas_proxy = True

    orch = Orchestrator(cfg)

    assert orch.config.ai.base_url == cfg.saas_api_url
    assert orch.config.ai.api_key == cfg.auth_token
