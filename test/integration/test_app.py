# Copyright (c) 2010-2026 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import pytest
from fastapi.testclient import TestClient

from src.app import api
from src.config import config
from src.modules.health.schema import HealthStatus


@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Pytest fixture that provides a TestClient for the FastAPI application.

    :return: TestClient instance bound to the FastAPI app.
    """
    return TestClient(api)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == HealthStatus.OK
    assert data["ai"]["provider"] == config.llm.openai_api_base
    assert data["ai"]["model"] == config.llm.model_name
    checks_by_name = {c["name"]: c for c in data["checks"]}
    assert checks_by_name["server"]["status"] == HealthStatus.OK
    assert checks_by_name["llm"]["status"] == HealthStatus.OK
    assert checks_by_name["langfuse"]["status"] == HealthStatus.DISABLED


def test_health_endpoint_llm_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.llm, "openai_api_key", "")

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == HealthStatus.ERROR
    checks_by_name = {c["name"]: c for c in data["checks"]}
    assert checks_by_name["server"]["status"] == HealthStatus.OK
    assert checks_by_name["llm"]["status"] == HealthStatus.ERROR
    assert "error" in checks_by_name["llm"]
