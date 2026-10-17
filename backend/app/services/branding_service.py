"""Brand of this installation and the subscription state (each client has their own installation).

Name, subtitle, colour and logo come from settings (BRAND_*); icons for the home screen are drawn from the
logo on the app's dark background. The subscription ends after SUBSCRIPTION_UNTIL (apiary calendar day).
"""
import hashlib
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image

from app.config import Settings
from app.schemas.common import today

DEFAULT_LOGO = Path(__file__).resolve().parent.parent / "assets" / "brand" / "logo.png"
BACKGROUND = (21, 18, 12, 255)  # --pitch
WARN_DAYS = 7


def logo_path(settings: Settings) -> Path:
    custom = Path(settings.brand_logo) if settings.brand_logo else None
    return custom if custom and custom.is_file() else DEFAULT_LOGO


def _version(path: Path) -> str:
    stat = path.stat()
    return hashlib.sha1(f"{path}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()[:10]


@lru_cache(maxsize=32)
def _render(path: str, version: str, size: int, scale: float, background: bool) -> bytes:
    logo = Image.open(path).convert("RGBA")
    logo.thumbnail((round(size * scale), round(size * scale)), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), BACKGROUND if background else (0, 0, 0, 0))
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    out = io.BytesIO()
    (canvas.convert("RGB") if background else canvas).save(out, "PNG", optimize=True)
    return out.getvalue()


def logo_png(settings: Settings) -> bytes:
    path = logo_path(settings)
    return _render(str(path), _version(path), 512, 1.0, False)


ICON_SIZES = {64: 0.9, 180: 0.86, 192: 0.86, 512: 0.86}


def icon_png(settings: Settings, size: int, maskable: bool = False) -> bytes:
    path = logo_path(settings)
    return _render(str(path), _version(path), size, 0.66 if maskable else ICON_SIZES[size], True)


def _shade(hex_colour: str, factor: float) -> str:
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    if factor >= 1:  # towards white
        mix = factor - 1
        r, g, b = (round(c + (255 - c) * mix) for c in (r, g, b))
    else:
        r, g, b = (round(c * factor) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def subscription(settings: Settings) -> dict:
    until = settings.subscription_until
    if until is None:
        return {"active": True, "days_left": None, "contact": settings.subscription_contact or None}
    left = (until - today()).days
    return {"active": left >= 0, "days_left": max(left, 0) if left <= WARN_DAYS else None,
            "contact": settings.subscription_contact or None}


def is_blocked(settings: Settings) -> bool:
    return settings.subscription_until is not None and today() > settings.subscription_until


def branding(settings: Settings) -> dict:
    v = _version(logo_path(settings))
    return {
        "name": settings.brand_name,
        "subtitle": settings.brand_subtitle,
        "color": settings.brand_color,
        "color_light": _shade(settings.brand_color, 1.3),
        "color_deep": _shade(settings.brand_color, 0.8),
        "logo_url": f"/api/branding/logo.png?v={v}",
        "icon_url": f"/api/branding/icon-180.png?v={v}",
        "subscription": subscription(settings),
    }


def manifest(settings: Settings) -> dict:
    v = _version(logo_path(settings))
    return {
        "id": "/",
        "name": settings.brand_name,
        "short_name": settings.brand_name[:24],
        "description": settings.brand_subtitle,
        "lang": "ru",
        "start_url": "/?source=homescreen",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#15120c",
        "theme_color": "#15120c",
        "icons": [
            {"src": f"/api/branding/icon-192.png?v={v}", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": f"/api/branding/icon-512.png?v={v}", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": f"/api/branding/icon-maskable-512.png?v={v}", "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }
