import pytest

from tests.test_dashboard_auth import authed, env  # noqa: F401


@pytest.mark.parametrize(("provider", "credentials", "ready"), [
    ("tinyfish", {"TINYFISH_API_KEY": "sample-tinyfish"}, {"tinyfish"}),
    ("serper", {"SERPER_API_KEY": "sample-serper"}, {"serper"}),
    ("scavio_maps", {"SCAVIO_API_KEY": "sample-scavio"}, {"scavio_maps", "scavio_search"}),
    ("dataforseo_listings", {
        "DATAFORSEO_LOGIN": "sample@example.test",
        "DATAFORSEO_PASSWORD": r"secret # with 'quotes' and \ slashes",
    }, {"dataforseo_listings", "dataforseo_serp", "dataforseo_maps"}),
])
def test_saved_credentials_survive_reload_and_ready_shared_sources(
        authed, env, monkeypatch, provider, credentials, ready):
    from huntly.config import load_env

    path = env["dir"] / ".env"
    path.write_text("# keep this comment\nSMTP_USERNAME=untouched@example.test\n", encoding="utf-8")
    monkeypatch.setenv("SMTP_USERNAME", "original@example.test")
    for name in credentials:
        monkeypatch.delenv(name, raising=False)
    result = authed.post("/api/discover/credentials", json={
        "provider": provider, "credentials": credentials,
    })
    assert result.status_code == 200
    assert result.json() == {"success": True}
    assert path.read_text(encoding="utf-8").startswith("# keep this comment\nSMTP_USERNAME=untouched@example.test\n")

    # Simulate a new dashboard process reading the saved file.
    for name in credentials:
        monkeypatch.delenv(name, raising=False)
    listing = authed.get("/api/discover/providers")
    assert ready <= {item["key"] for item in listing.json()["providers"] if item["configured"]}
    for name, value in credentials.items():
        assert getattr(load_env(), name.lower()) == value
        assert value not in listing.text
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("body", [
    {"provider": "osm", "credentials": {"SERPER_API_KEY": "x"}},
    {"provider": "serper", "credentials": {"SMTP_USERNAME": "x"}},
    {"provider": "dataforseo_maps", "credentials": {"DATAFORSEO_LOGIN": "login"}},
    {"provider": "serper", "credentials": {"SERPER_API_KEY": "your_api_key_here"}},
    {"provider": "serper", "credentials": {"SERPER_API_KEY": "foo\nSMTP_USERNAME=injected"}},
])
def test_refuses_invalid_credentials_without_writing(authed, env, body):
    result = authed.post("/api/discover/credentials", json=body)
    assert result.status_code == 400
    assert not (env["dir"] / ".env").exists()
