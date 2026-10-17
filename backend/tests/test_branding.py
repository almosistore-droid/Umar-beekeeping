"""Subscription for clients: each installation has its own brand; after the paid date the app is closed."""
import io
from datetime import timedelta

import pytest
from PIL import Image
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas.common import today as app_today

TODAY = app_today()


@pytest.fixture
def brand(monkeypatch, tmp_path):
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (300, 200), (10, 120, 200, 255)).save(logo)
    s = get_settings()
    for k, v in {"brand_name": "Asal Pro", "brand_subtitle": "Учёт пасеки", "brand_color": "#2f80ed",
                 "brand_logo": str(logo), "subscription_contact": "+992 90 000-00-00"}.items():
        monkeypatch.setattr(s, k, v)
    return s


def until(monkeypatch, days: int | None):
    monkeypatch.setattr(get_settings(), "subscription_until", None if days is None else TODAY + timedelta(days=days))


def png_size(content: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(content)).size


def test_default_brand_is_public(client):
    r = client.get("/api/branding")
    assert r.status_code == 200
    b = r.json()
    assert b["name"] == "Fayzi Umar" and b["color"] == "#f4c23b" and b["logo_url"].startswith("/api/branding/logo.png?v=")
    assert b["subscription"] == {"active": True, "days_left": None, "contact": None}


def test_client_brand_logo_icons_manifest(client, brand):
    b = client.get("/api/branding").json()
    assert b["name"] == "Asal Pro" and b["color"] == "#2f80ed" and b["color_deep"] == "#2666be"
    logo = client.get(b["logo_url"])
    assert logo.headers["content-type"] == "image/png" and png_size(logo.content) == (512, 512)
    for size in (64, 180, 192, 512):
        assert png_size(client.get(f"/api/branding/icon-{size}.png").content) == (size, size)
    assert png_size(client.get("/api/branding/icon-maskable-512.png").content) == (512, 512)
    assert client.get("/api/branding/icon-100.png").status_code == 404
    m = client.get("/api/branding/manifest.webmanifest")
    assert m.headers["content-type"].startswith("application/manifest+json")
    assert m.json()["name"] == "Asal Pro" and m.json()["icons"][0]["src"].startswith("/api/branding/icon-192.png")


def test_brand_in_files_and_messages(client, brand, as_role):
    admin = as_role("ADMIN", 1000)
    r = client.post("/api/admin/invites", json={"telegram_id": 7100, "role": "VIEWER"}, headers=admin)
    assert "учёт пасеки Asal Pro" in r.json()["share_text"]
    pdf = client.get(f"/api/reports/yearly/{TODAY.year}/export", params={"format": "pdf"}, headers=admin)
    assert b"Asal Pro" in pdf.content


def test_warning_in_the_last_week(client, monkeypatch):
    until(monkeypatch, 3)
    assert client.get("/api/branding").json()["subscription"] == {"active": True, "days_left": 3, "contact": None}
    until(monkeypatch, 30)
    assert client.get("/api/branding").json()["subscription"]["days_left"] is None
    until(monkeypatch, 0)  # the last paid day still works
    assert client.get("/api/branding").json()["subscription"] == {"active": True, "days_left": 0, "contact": None}


def test_closed_after_the_paid_date(client, brand, monkeypatch, login, as_role):
    headers = as_role("BEEKEEPER", 3000)
    until(monkeypatch, -1)
    assert client.get("/api/branding").json()["subscription"] == {"active": False, "days_left": 0,
                                                                  "contact": "+992 90 000-00-00"}
    r = client.get("/api/hives", headers=headers)
    assert r.status_code == 402 and r.json()["detail"].startswith("Подписка закончилась")
    from tests.conftest import make_init_data
    assert client.post("/api/auth/telegram", json={"init_data": make_init_data(3000)}).status_code == 402
    assert client.post("/api/auth/password", json={"login": "x", "password": "y"}).status_code == 402
    assert client.post("/api/notifications/dispatch").status_code == 402  # reminders stop too
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/branding/logo.png").status_code == 200
    tg = client.get("/api/hives", headers={**headers, "X-Lang": "tg"})
    assert tg.json()["detail"].startswith("Обуна ба охир расид")
    until(monkeypatch, 30)  # renewed: works again at once
    assert client.get("/api/hives", headers=headers).status_code == 200


def test_settings_validation():
    with pytest.raises(ValidationError):
        Settings(brand_color="gold")
    assert Settings(subscription_until="").subscription_until is None
    assert str(Settings(subscription_until="2027-01-31").subscription_until) == "2027-01-31"
