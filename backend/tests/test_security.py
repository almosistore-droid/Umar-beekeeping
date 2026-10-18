"""Stage 10 (security): tokens, headers, published API description, roles on every data endpoint."""
import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import create_app


def test_no_cache_and_nosniff_on_data(client, beekeeper):
    r = client.get("/api/hives", headers=beekeeper)
    assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"
    logo = client.get("/api/branding/logo.png")
    assert "no-store" not in logo.headers.get("cache-control", "")


def test_api_description_is_hidden_in_production(monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "production")
    with TestClient(create_app()) as prod:
        assert prod.get("/api/docs").status_code == 404
        assert prod.get("/api/openapi.json").status_code == 404
    with TestClient(create_app()):
        pass


def test_tokens_with_other_algorithms_or_keys_are_refused(client, beekeeper):
    user_id = str(uuid.uuid4())
    now = int(time.time())
    claims = {"sub": user_id, "iat": now, "exp": now + 600, "type": "access", "role": "ADMIN"}
    unsigned = jwt.encode(claims, key="", algorithm="none")
    other_key = jwt.encode(claims, "another-secret-another-secret-0123456", algorithm="HS256")
    expired = jwt.encode({**claims, "exp": now - 10}, get_settings().jwt_secret, algorithm="HS256")
    refresh = jwt.encode({**claims, "type": "refresh"}, get_settings().jwt_secret, algorithm="HS256")
    for token in (unsigned, other_key, expired, refresh, "garbage"):
        assert client.get("/api/hives", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_jwt_algorithm_cannot_be_none():
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql+psycopg://x", telegram_bot_token="1:x", jwt_secret="s" * 40, jwt_algorithm="none")


def test_every_data_endpoint_needs_a_login(client):
    """All routes except the public ones answer 401 without a token (no forgotten endpoint)."""
    public = ("/api/health", "/api/branding", "/api/auth/", "/api/owner/", "/api/notifications/dispatch",
              "/api/docs", "/api/redoc", "/api/openapi.json")
    open_routes = []
    for route in client.app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/") or path.startswith(public):
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            url = path.replace("{", "").replace("}", "")
            for name in ("hive_id", "id", "item_id", "batch_id", "key", "year", "slug", "harvest_id"):
                url = url.replace(name, "1" if name == "year" else str(uuid.uuid4()) if name != "key" else "acceptance")
            r = client.request(method, url)
            if r.status_code not in (401, 422):  # 422: path didn't parse before auth — still not served
                open_routes.append((method, path, r.status_code))
    assert not open_routes, open_routes
