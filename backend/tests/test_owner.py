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


def test_user_management_moves_to_the_owner_panel(client, owner_token, as_role):
    admin = as_role("ADMIN", 3100)
    assert client.get("/api/users", headers=admin).status_code == 200
    assert client.get("/api/branding").json()["admin_in_app"] is True

    assert client.put("/api/owner/settings", json={"admin_in_app": False}, headers=H()).json() == {"admin_in_app": False}
    assert client.get("/api/branding").json()["admin_in_app"] is False
    assert client.get("/api/owner/stats", headers=H()).json()["admin_in_app"] is False
    for path in ("/api/users", "/api/admin/overview", "/api/admin/invites", "/api/admin/audit"):
        r = client.get(path, headers=admin)
        assert r.status_code == 403 and "панели владельца" in r.json()["detail"], path
    assert client.post("/api/admin/accounts", json={"first_name": "A", "login": "aaaa", "role": "VIEWER"},
                       headers=admin).status_code == 403
    # the rest of the app still works for the client's admin
    assert client.get("/api/hives", headers=admin).status_code == 200

    # the owner manages users instead
    data = client.get("/api/owner/users", headers=H()).json()
    me = next(u for u in data["users"] if u["telegram_id"] == 3100)
    r = client.patch(f"/api/owner/users/{me['id']}", json={"role": "BEEKEEPER", "is_active": False}, headers=H())
    assert r.status_code == 200 and r.json()["role"] == "BEEKEEPER" and r.json()["is_active"] is False
    r = client.post("/api/owner/accounts", json={"first_name": "Сабина", "login": "sabina", "role": "ASSISTANT"},
                    headers=H())
    assert r.status_code == 201 and len(r.json()["temporary_password"]) >= 8
    r = client.post(f"/api/owner/users/{me['id']}/password", json={"login": "umar"}, headers=H())
    assert r.status_code == 200 and r.json()["login"] == "umar"
    inv = client.post("/api/owner/invites", json={"username": "new_helper", "role": "VIEWER"}, headers=H())
    assert inv.status_code == 201 and inv.json()["kind"] == "invited"
    assert client.post(f"/api/owner/invites/{inv.json()['invite']['id']}/revoke", headers=H()).status_code == 200
    log = client.get("/api/owner/audit", headers=H()).json()["items"]
    assert {"admin_place_set", "updated", "account_created", "password_reset", "invited", "invite_revoked"} <= \
        {x["action"] for x in log}
    assert all(x["comment"] == "Панель владельца" for x in log if x["action"] in ("account_created", "invited"))

    client.put("/api/owner/settings", json={"admin_in_app": True}, headers=H())
    admin2 = as_role("ADMIN", 3101)
    assert client.get("/api/users", headers=admin2).status_code == 200


def test_admin_in_app_setting_from_env(client, owner_token, monkeypatch, as_role):
    admin = as_role("ADMIN", 3200)
    monkeypatch.setattr(get_settings(), "admin_in_app", False)
    assert client.get("/api/admin/overview", headers=admin).status_code == 403
    client.put("/api/owner/settings", json={"admin_in_app": True}, headers=H())  # the panel wins over the .env
    assert client.get("/api/admin/overview", headers=admin).status_code == 200


def test_panel_users_page(owner_panel, client, as_role):
    as_role("BEEKEEPER", 3300)
    login(owner_panel)
    home = owner_panel.get("/").text
    assert "Пользователи и доступ" in home and "в приложении" in home
    csrf = re.search(r"name='csrf' value='([0-9a-f]+)'", home).group(1)
    owner_panel.post("/clients/asal/settings", data={"admin_in_app": "0", "csrf": csrf})
    assert "только здесь" in owner_panel.get("/").text

    page = owner_panel.get("/clients/asal/users").text
    assert "Пользователи (1)" in page and "Telegram ID 3300" in page
    uid = re.search(r"/clients/asal/users/([0-9a-f-]{36})'", page).group(1)

    # without the form token nothing changes
    owner_panel.post(f"/clients/asal/users/{uid}", data={"role": "VIEWER"})
    assert client.get("/api/owner/users", headers=H()).json()["users"][0]["role"] == "BEEKEEPER"

    r = owner_panel.post(f"/clients/asal/users/{uid}", data={"role": "ADMIN", "is_active": "1", "csrf": csrf})
    assert "Сохранено" in r.text
    assert client.get("/api/owner/users", headers=H()).json()["users"][0]["role"] == "ADMIN"

    r = owner_panel.post(f"/clients/asal/users/{uid}/password", data={"login": "x", "csrf": csrf})
    assert "Данные для входа" not in r.text  # login too short → the app's error message instead
    r = owner_panel.post(f"/clients/asal/users/{uid}/password", data={"login": "umar", "csrf": csrf})
    assert "Данные для входа" in r.text and "umar" in r.text

    r = owner_panel.post("/clients/asal/accounts", data={"first_name": "Сабина", "login": "sabina",
                                                          "role": "ASSISTANT", "csrf": csrf})
    assert "Данные для входа" in r.text and "sabina" in r.text
    r = owner_panel.post("/clients/asal/accounts", data={"first_name": "Ещё", "login": "sabina",
                                                          "role": "ASSISTANT", "csrf": csrf})
    assert "уже занят" in r.text

    r = owner_panel.post("/clients/asal/invites", data={"who": "@new_helper", "role": "VIEWER", "csrf": csrf})
    assert "Приглашение создано" in r.text and "@new_helper" in r.text
    iid = re.search(r"/invites/([0-9a-f-]{36})/revoke", r.text).group(1)
    r = owner_panel.post(f"/clients/asal/invites/{iid}/revoke", data={"csrf": csrf})
    assert "Приглашение отозвано" in r.text and "@new_helper" not in r.text
    r = owner_panel.post("/clients/asal/invites", data={"who": "3300", "role": "VIEWER", "csrf": csrf})
    assert "роль изменена" in r.text

    log = owner_panel.get("/clients/asal/log").text
    assert "Панель владельца" in log and "вход по паролю создан" in log
    assert owner_panel.get("/clients/nobody/users", follow_redirects=False).status_code == 303
    assert "нет OWNER_TOKEN" in owner_panel.get("/clients/old/users").text
