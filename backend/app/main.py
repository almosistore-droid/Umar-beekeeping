import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import i18n
from app.config import get_settings
from app.routers import admin, apiaries, auth, health, hives, queens, users
from app.routers import branding, crm, notifications, operations, owner, qr, rearing, records, reports, stock
from app.services import branding_service
from app.utils.errors import DomainError
from app.utils.validation_messages import humanize_errors


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.environment == "production":
        settings.assert_production_ready()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Lang"],
    )

    @app.middleware("http")
    async def subscription(request: Request, call_next):
        """After SUBSCRIPTION_UNTIL the whole app is closed (except health and the public brand)."""
        path = request.url.path
        # /api/owner: the owner panel must reach a closed client to extend it (protected by OWNER_TOKEN)
        if (path.startswith("/api/") and not path.startswith(("/api/health", "/api/branding", "/api/owner"))
                and branding_service.is_blocked(get_settings())):
            return JSONResponse(status_code=402, content={
                "detail": "Подписка закончилась. Обратитесь к поставщику, чтобы продлить доступ."})
        return await call_next(request)

    @app.middleware("http")
    async def language(request: Request, call_next):
        """X-Lang: ru|tg — answers (errors, labels, timeline…) in the user's language."""
        lang = i18n.normalize(request.headers.get("x-lang"))
        token = i18n.current_lang.set(lang)
        try:
            response = await call_next(request)
        finally:
            i18n.current_lang.reset(token)
        if lang == i18n.DEFAULT or not response.headers.get("content-type", "").startswith("application/json"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return JSONResponse(i18n.translate_json(json.loads(body), lang), status_code=response.status_code, headers=headers)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        # Human-readable Russian errors for the Mini App, with the field each belongs to
        errors = humanize_errors(exc.errors())
        detail = "Проверьте введённые данные"
        if errors:
            detail += ": " + errors[0]["message"]
        return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})

    @app.exception_handler(DomainError)
    async def domain_handler(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(IntegrityError)
    async def integrity_handler(_: Request, exc: IntegrityError):
        # Last line of defence: DB constraints caught something the services did not
        return JSONResponse(
            status_code=409,
            content={"detail": "Данные противоречат уже сохранённым записям. Обновите страницу и попробуйте снова."},
        )

    app.include_router(health.router)
    app.include_router(branding.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(admin.router)
    app.include_router(apiaries.router)
    app.include_router(hives.router)
    app.include_router(queens.router)
    app.include_router(records.router)
    app.include_router(operations.router)
    app.include_router(qr.router)
    app.include_router(reports.router)
    app.include_router(crm.router)
    app.include_router(notifications.router)
    app.include_router(stock.router)
    app.include_router(rearing.router)
    app.include_router(owner.router)
    return app


app = create_app()
