"""Owner of the subscription: per-installation owner API (token) and the owner panel over all clients."""
import re
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app as backend_app
from app.owner_panel import main as panel
from app.schemas.common import today as app_today

TODAY = app_today()
TOKEN = "o" * 40


@pytest.fixture
def owner_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "owner_token", TOKEN)
    monkeypatch.setattr(get_settings(), "subscription_until", TODAY + timedelta(days=30))


def H(token=TOKEN):  # noqa: N802
    return {"X-Owner-Token": token}


def test_owner_api_is_off_without_a_token(client):
    assert client.get("/api/owner/stats", headers=H()).status_code == 404


def test_owner_api_needs_the_right_token(client, owner_token):
    assert client.get("/api/owner/stats").status_code == 401
    assert client.get("/api/owner/stats", headers=H("x" * 40)).status_code == 401
    r = client.get("/api/owner/stats", headers=H())
    assert r.status_code == 200
    s = r.json()
    assert s["subscription"]["until"] == str(TODAY + timedelta(days=30)) and s["subscription"]["source"] == "env"
    assert s["hives"] == 0 and s["users"] == {"active": 0, "total": 0} and s["schema"]


def test_panel_date_overrides_env_and_blocks_or_opens(client, owner_token, beekeeper):
    assert client.get("/api/hives", headers=beekeeper).status_code == 200
    r = client.put("/api/owner/subscription", json={"until": str(TODAY - timedelta(days=1))}, headers=H())
    assert r.status_code == 200 and r.json()["blocked"] is True
    assert client.get("/api/hives", headers=beekeeper).status_code == 402
    assert client.get("/api/branding").json()["subscription"]["active"] is False
    # the owner can still reach a closed client and open it again
    assert client.get("/api/owner/stats", headers=H()).json()["subscription"]["source"] == "panel"
    client.put("/api/owner/subscription", json={"until": None}, headers=H())
    assert client.get("/api/hives", headers=beekeeper).status_code == 200
    assert client.get("/api/branding").json()["subscription"] == {"active": True, "days_left": None, "contact": None}


def test_server_command_sets_and_shows(owner_token, capsys):
    from app.utils.subscription import main
    assert main(["set", "2030-05-01"]) == 0
    capsys.readouterr()
    assert main(["show"]) == 0
    assert capsys.readouterr().out.strip() == "2030-05-01"
    assert main(["set", "none"]) == 0 and main(["show"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "none"
    assert main(["bad"]) == 2


def test_extension_dates():
    t = date(2026, 10, 18)
    assert panel.new_until("month", date(2027, 1, 31), "", t) == (True, date(2027, 2, 28))
    assert panel.new_until("year", date(2026, 1, 1), "", t) == (True, date(2027, 10, 18))  # passed → from today
    assert panel.new_until("block", None, "", t) == (True, date(2026, 10, 17))
    assert panel.new_until("unlimited", None, "", t) == (True, None)
    assert panel.new_until("date", None, "2027-03-01", t) == (True, date(2027, 3, 1))
    assert panel.new_until("date", None, "", t)[0] is False


@pytest.fixture
def owner_panel(tmp_path, monkeypatch, owner_token):
    (tmp_path / "asal.env").write_text(f"DOMAIN=asal.tj\nBRAND_NAME=Asal Pro\nOWNER_TOKEN={TOKEN}\n", encoding="utf-8")
    (tmp_path / "old.env").write_text("DOMAIN=old.tj\nBRAND_NAME=Old\n", encoding="utf-8")
    monkeypatch.setenv("OWNER_CLIENTS_DIR", str(tmp_path))
    monkeypatch.setenv("OWNER_PASSWORD", "correct-horse-battery")
    monkeypatch.setenv("OWNER_SECRET", "s" * 48)
    monkeypatch.setenv("OWNER_BACKEND_URL", "http://backend-{slug}")
    monkeypatch.setenv("OWNER_INSECURE_COOKIE", "1")
    monkeypatch.setattr(panel, "transport", httpx.ASGITransport(app=backend_app))
    panel._fails.clear()
    with TestClient(panel.app) as c:
        yield c


def login(c, password="correct-horse-battery"):
    return c.post("/login", data={"password": password}, follow_redirects=False)


def test_panel_login_and_lockout(owner_panel):
    assert "Пароль" in owner_panel.get("/").text
    for _ in range(5):
        assert "Неверный пароль" in login(owner_panel, "nope").text
    assert "Слишком много попыток" in login(owner_panel).text


def test_panel_lists_clients_and_extends(owner_panel, client):
    r = login(owner_panel)
    assert r.status_code == 303
    page = owner_panel.get("/").text
    assert "Fayzi Umar" in page and "asal.tj" in page and "оплачено" in page  # brand as the installation reports it
    assert "нет OWNER_TOKEN" in page  # the client without a token is shown with the fix
    csrf = re.search(r"name='csrf' value='([0-9a-f]+)'", page).group(1)

    # without the form token nothing changes
    owner_panel.post("/clients/asal/subscription", data={"action": "block"}, follow_redirects=False)
    assert client.get("/api/owner/stats", headers=H()).json()["subscription"]["source"] == "env"

    r = owner_panel.post("/clients/asal/subscription", data={"action": "year", "csrf": csrf}, follow_redirects=False)
    assert r.status_code == 303
    until = client.get("/api/owner/stats", headers=H()).json()["subscription"]["until"]
    assert until == str(panel.add_months(TODAY + timedelta(days=30), 12))
    owner_panel.post("/clients/asal/subscription", data={"action": "block", "csrf": csrf})
    assert "доступ закрыт" in owner_panel.get("/").text


def test_panel_pages_are_not_framed_or_cached(owner_panel):
    r = owner_panel.get("/")
    assert r.headers["x-frame-options"] == "DENY" and "no-store" in r.headers["cache-control"]
