"""Public brand of this installation (no login needed: the login screen and home-screen icon show it)."""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services import branding_service

router = APIRouter(prefix="/api/branding", tags=["branding"])
CACHE = {"Cache-Control": "public, max-age=86400"}


@router.get("")
def branding():
    return branding_service.branding(get_settings())


@router.get("/logo.png")
def logo():
    return Response(branding_service.logo_png(get_settings()), media_type="image/png", headers=CACHE)


@router.get("/icon-maskable-512.png")
def icon_maskable():
    return Response(branding_service.icon_png(get_settings(), 512, maskable=True), media_type="image/png", headers=CACHE)


@router.get("/icon-{size}.png")
def icon(size: int):
    if size not in branding_service.ICON_SIZES:
        raise HTTPException(404, "Нет такого размера")
    return Response(branding_service.icon_png(get_settings(), size), media_type="image/png", headers=CACHE)


@router.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(branding_service.manifest(get_settings()), media_type="application/manifest+json")
