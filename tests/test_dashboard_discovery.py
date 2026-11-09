import pytest

from tests.test_dashboard_auth import authed, env  # noqa: F401


@pytest.fixture(autouse=True)
def discovery_job(monkeypatch):
    from unittest.mock import AsyncMock

    import huntly.dashboard as dash
    from huntly import pipeline

    run = AsyncMock(return_value=pipeline.PipelineReport())
    monkeypatch.setattr(pipeline, "run_prospecting", run)
    monkeypatch.setattr(dash, "_discovery_task", None)
    monkeypatch.setattr(dash, "_discovery_report", None)
    return run


@pytest.mark.parametrize("endpoint", ["estimate", "run"])
@pytest.mark.parametrize("payload", [
    [],
    {"provider": ["osm"]},
    {"provider": "osm", "cities": "Denver, CO"},
    {"provider": "osm", "cities": [123]},
    {"provider": "osm", "limit": 0},
    {"provider": "osm", "depth": 10.5},
])
def test_invalid_search_parameters_are_rejected(authed, endpoint, payload):
    response = authed.post(f"/api/discover/{endpoint}", json=payload)
    assert response.status_code == 400


@pytest.mark.parametrize("cap", ["NaN", "Infinity", -1, True])
def test_invalid_discovery_cap_is_rejected(authed, cap):
    response = authed.post("/api/discover/run", json={"provider": "osm", "max_spend": cap})
    assert response.status_code == 400
    assert "spend cap" in response.json()["message"]


def test_run_respects_explicit_zero_spend_cap(authed, discovery_job):
    import huntly.dashboard as dash

    response = authed.post("/api/discover/run", json={"provider": "osm", "max_spend": 0})
    assert response.json()["success"]

    async def wait_for_run():
        await dash._discovery_task

    authed.portal.call(wait_for_run)
    assert discovery_job.await_args.kwargs["max_spend"] == 0
