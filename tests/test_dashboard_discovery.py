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


@pytest.mark.asyncio
async def test_parallel_discovery_requests_only_start_one_job(env, monkeypatch, discovery_job):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import httpx

    import huntly.dashboard as dash

    first_starting = asyncio.Event()
    release_first = asyncio.Event()

    async def init_db():
        if first_starting.is_set():
            release_first.set()
        first_starting.set()
        await release_first.wait()

    state = SimpleNamespace(init_db=init_db, set_setting=AsyncMock())
    monkeypatch.setattr(dash, "_state", lambda: state)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=dash.app),
        base_url="http://127.0.0.1:5555",
        headers={"Authorization": f"Bearer {env['token']}"},
    ) as client:
        first = asyncio.create_task(client.post("/api/discover/run", json={"provider": "osm"}))
        try:
            await asyncio.wait_for(first_starting.wait(), timeout=3)
            second = await asyncio.wait_for(
                client.post("/api/discover/run", json={"provider": "osm"}), timeout=3,
            )
            assert second.status_code == 409
        finally:
            release_first.set()
            assert (await first).status_code == 200
    await dash._discovery_task
    discovery_job.assert_awaited_once()
