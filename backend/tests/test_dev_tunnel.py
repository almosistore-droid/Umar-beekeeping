"""Dev tunnel supervisor (tunnel/tunnel.py): address parsing, Telegram menu button, health and restart logic."""
import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("dev_tunnel", Path(__file__).resolve().parents[2] / "tunnel" / "tunnel.py")
tunnel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tunnel)


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", status=200):
        super().__init__(body)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_find_url_from_cloudflared_output():
    line = "2026-10-13T17:52:22Z INF |  https://roberts-collectible-jail-highly.trycloudflare.com                |"
    assert tunnel.find_url(line) == "https://roberts-collectible-jail-highly.trycloudflare.com"
    assert tunnel.find_url("INF Requesting new quick Tunnel on trycloudflare.com...") is None
    assert tunnel.find_url('ERR failed to request quick Tunnel: Post "https://api.trycloudflare.com/tunnel"') is None


def test_token_usable():
    assert tunnel.token_usable("7000000000:AAH-real")
    assert not tunnel.token_usable("")
    assert not tunnel.token_usable("1234567890:local-test-token")
    assert not tunnel.token_usable("nonsense")


def test_set_menu_button_sends_web_app_button():
    sent = {}

    def opener(req, timeout):
        sent.update(url=req.full_url, body=json.loads(req.data))
        return FakeResponse(b'{"ok": true, "result": true}')

    assert tunnel.set_menu_button("123:abc", "https://x.trycloudflare.com", "Пасека", opener=opener)
    assert sent["url"] == "https://api.telegram.org/bot123:abc/setChatMenuButton"
    assert sent["body"] == {"menu_button": {"type": "web_app", "text": "Пасека", "web_app": {"url": "https://x.trycloudflare.com"}}}


def test_set_menu_button_failure_is_reported_not_raised(capsys):
    def opener(req, timeout):
        raise urllib.error.URLError("no network")

    assert tunnel.set_menu_button("123:abc", "https://x.trycloudflare.com", "Пасека", opener=opener) is False
    assert "не удалось обновить кнопку" in capsys.readouterr().out


@pytest.mark.parametrize("behaviour, alive", [
    (lambda: FakeResponse(b"<html>", 200), True),
    (lambda: (_ for _ in ()).throw(urllib.error.HTTPError("u", 530, "Origin DNS error", {}, None)), False),
    (lambda: (_ for _ in ()).throw(urllib.error.HTTPError("u", 404, "Not found", {}, None)), False),
    (lambda: (_ for _ in ()).throw(urllib.error.URLError("Name or service not known")), False),
])
def test_is_alive(behaviour, alive):
    assert tunnel.is_alive("https://x.trycloudflare.com", opener=lambda req, timeout: behaviour()) is alive


class Stop(Exception):
    pass


def test_dead_address_leads_to_a_new_tunnel(monkeypatch):
    """After MAX_FAILURES failed checks the supervisor stops cloudflared and starts a new tunnel."""
    sup = tunnel.Supervisor("http://frontend:5173", "", "Пасека")
    events = []

    class Proc:
        def poll(self):
            return None

    def fake_start():
        events.append("start")
        if events.count("start") == 2:
            raise Stop
        sup.proc, sup.url = Proc(), "https://old.trycloudflare.com"
        return True

    monkeypatch.setattr(sup, "start", fake_start)
    monkeypatch.setattr(sup, "stop", lambda: events.append("stop"))
    monkeypatch.setattr(tunnel, "is_alive", lambda url: False)
    monkeypatch.setattr(tunnel.time, "sleep", lambda s: None)
    with pytest.raises(Stop):
        sup.run_forever()
    assert events == ["start", "stop", "start"]


def test_healthy_tunnel_keeps_running_and_survives_a_blip(monkeypatch):
    sup = tunnel.Supervisor("http://frontend:5173", "", "Пасека")
    checks = iter([True, False, True, False, False, True] + [True] * 3)

    class Proc:
        def poll(self):
            return None

    sup.proc, sup.url = Proc(), "https://ok.trycloudflare.com"
    monkeypatch.setattr(sup, "start", lambda: True)
    stops = []
    monkeypatch.setattr(sup, "stop", lambda: stops.append(1))

    def alive(url):
        try:
            return next(checks)
        except StopIteration:
            raise Stop

    monkeypatch.setattr(tunnel, "is_alive", alive)
    monkeypatch.setattr(tunnel.time, "sleep", lambda s: None)
    with pytest.raises(Stop):
        sup.run_forever()
    assert stops == []  # never 4 failures in a row → never restarted
