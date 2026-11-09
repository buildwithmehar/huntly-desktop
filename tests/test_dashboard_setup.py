"""First-run setup persists the same settings the outreach loop reads."""

from pathlib import Path

import pytest
import yaml

import huntly.dashboard as dash
from huntly.config import load_config
from tests.test_dashboard_auth import authed, env  # noqa: F401


@pytest.mark.parametrize("payload", ["[]", "null", '{"api_key":123}', '{"api_key":"abc\\nxyz"}'])
def test_instantly_rejects_malformed_credentials(authed, payload, monkeypatch):
    from unittest.mock import Mock

    import httpx

    connection = Mock(side_effect=AssertionError("Unexpected network request"))
    monkeypatch.setattr(httpx, "AsyncClient", connection)
    response = authed.post("/api/settings/test-instantly", content=payload,
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    connection.assert_not_called()


@pytest.fixture
def workspace(env, monkeypatch):
    base = env["dir"] / "huntly.yaml"
    local = base.with_name("huntly.local.yaml")
    base.write_bytes((Path(dash.PACKAGE_ROOT) / base.name).read_bytes())
    monkeypatch.setattr(dash, "PROJECT_ROOT", env["dir"])
    monkeypatch.setattr(dash, "_resolve_config_file", lambda: local if local.exists() else base)
    return base, local


def test_first_profile_replaces_sample_copy_and_keeps_approval(authed, workspace):
    base, local = workspace
    before = base.read_bytes()
    profile = {
        "name": "Sam Rivera", "company": "North Studio", "email": "sam@north.example",
        "product": "Packaging design", "description": "Packaging for independent food brands",
        "industries": "Food brands\nCoffee roasters", "titles": "Founder",
        "geography": "Lahore, Pakistan", "postal_address": "10 Test Street, Lahore",
    }
    response = authed.post("/api/settings/setup", json={"profile": profile})
    assert response.status_code == 200, response.text
    saved = load_config(str(local))
    assert saved.persona.company == "North Studio"
    assert saved.icp.geography == ["Lahore, Pakistan"]
    assert saved.product.key_benefits == [] and saved.product.objection_responses == {}
    assert saved.product.offer.goal == "get_reply"
    assert saved.compliance.postal_address == "10 Test Street, Lahore"
    assert saved.channels.email.require_approval
    assert base.read_bytes() == before
    assert authed.get("/api/settings/setup").json()["profile"] == profile


def test_provider_change_preserves_existing_settings(authed, workspace):
    base, local = workspace
    data = yaml.safe_load(base.read_text(encoding="utf-8"))
    data["brain"] = {"provider": "claude", "model": "sonnet"}
    data["channels"]["email"]["require_approval"] = False
    local.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert authed.post("/api/settings/setup", json={"email_provider": "smtp"}).status_code == 200
    saved = load_config(str(local))
    assert saved.channels.email.provider == "smtp"
    assert saved.channels.email.require_approval
    assert saved.brain.model == "sonnet"


def test_invalid_setup_does_not_write_files(authed, workspace):
    base, local = workspace
    before = base.read_bytes()
    response = authed.post("/api/settings/setup", json={"email_provider": "invalid"})
    assert response.status_code == 400
    assert base.read_bytes() == before and not local.exists()


@pytest.mark.parametrize("provider", ["gmail", "microsoft"])
@pytest.mark.parametrize("encoding", ["utf-8", "cp1252"])
def test_mailbox_connect_uses_saved_credentials(authed, workspace, env, monkeypatch, provider, encoding):
    from huntly.integrations import gmail, microsoft
    from huntly import textio

    monkeypatch.setattr(textio.locale, "getencoding", lambda: "cp1252")
    calls = []

    def authorize(client, secondary):
        calls.append((client, secondary))
        return True

    if provider == "gmail":
        monkeypatch.setattr(gmail, "run_auth_flow", authorize)
        credentials = "GMAIL_CLIENT_ID=example\nGMAIL_CLIENT_SECRET=example-secret\n"
        expected = ("example", "example-secret")
    else:
        monkeypatch.setattr(microsoft, "run_auth_flow", authorize)
        credentials = "M365_CLIENT_ID=example\nM365_TENANT_ID=example-tenant\n"
        expected = ("example", "example-tenant")
    (env["dir"] / ".env").write_text("# Café setup\n" + credentials, encoding=encoding)
    response = authed.post("/api/settings/mail-auth", json={"provider": provider})
    assert response.json() == {"success": True}
    assert calls == [expected]
