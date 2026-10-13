from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.routers import apiaries, auth, health, hives, queens, users
from app.routers import operations, qr, records, reports
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
        allow_headers=["Authorization", "Content-Type"],
    )

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
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(apiaries.router)
    app.include_router(hives.router)
    app.include_router(queens.router)
    app.include_router(records.router)
    app.include_router(operations.router)
    app.include_router(qr.router)
    app.include_router(reports.router)
    return app


app = create_app()
