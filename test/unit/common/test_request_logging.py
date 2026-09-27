import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.app import create_api
from src.common.logger import RequestContextFilter, request_id
from src.modules.health.schema import HealthResponse, HealthStatus


def test_log_filter_reads_current_request_context():
    record = logging.makeLogRecord({"msg": "test"})
    context_filter = RequestContextFilter()
    token = request_id.set("test-request")
    try:
        assert context_filter.filter(record)
        assert record.request_id == "test-request"
    finally:
        request_id.reset(token)
    context_filter.filter(record)
    assert record.request_id == "-"


def test_successful_health_check_is_debug_only(caplog):
    result = HealthResponse(status=HealthStatus.OK, version="test", checks=[])
    with patch("src.app.run_health_checks", new=AsyncMock(return_value=result)):
        with caplog.at_level(logging.DEBUG, logger="src.app"), TestClient(create_api()) as client:
            assert client.get("/health").status_code == 200
    records = [r for r in caplog.records if r.name == "src.app"]
    assert any("Request completed" in r.message for r in records)
    assert all(r.levelno == logging.DEBUG for r in records)


@pytest.mark.parametrize("status, level", [(200, logging.INFO), (422, logging.WARNING), (503, logging.ERROR)])
def test_request_summary(status, level, caplog):
    app = create_api()
    observed_ids = []

    @app.get("/logging-test")
    async def endpoint():
        observed_ids.append(request_id.get())
        if status != 200:
            raise HTTPException(status_code=status)
        return {"ok": True}

    with caplog.at_level(logging.DEBUG, logger="src.app"), TestClient(app) as client:
        first = client.get("/logging-test?secret=do-not-log")
        second = client.get("/logging-test")

    assert first.status_code == status
    assert first.headers["X-Request-ID"] == observed_ids[0]
    assert second.headers["X-Request-ID"] == observed_ids[1]
    assert observed_ids[0] != observed_ids[1]
    assert request_id.get() == "-"
    records = [r for r in caplog.records if r.name == "src.app" and "Request completed" in r.message]
    assert len(records) == 2
    assert all(r.levelno == level and "duration_ms=" in r.message for r in records)
    assert all("secret" not in r.message for r in caplog.records if r.name == "src.app")


def test_unhandled_failure_logs_type_without_exception_contents(caplog):
    app = create_api()

    @app.get("/logging-failure")
    async def endpoint():
        raise RuntimeError("sensitive payload")

    with caplog.at_level(logging.DEBUG, logger="src.app"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/logging-failure")

    assert response.status_code == 500
    assert "error_type=RuntimeError" in caplog.text
    assert "sensitive payload" not in caplog.text
    assert request_id.get() == "-"
