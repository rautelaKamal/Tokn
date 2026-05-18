from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Future: warm DB pool, Redis, etc.
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    # Rate limiter — attached to app state
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API key auth middleware — skips health check and docs
    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        # Skip auth if no key is configured (dev mode)
        if not settings.tokn_api_key:
            return await call_next(request)

        # Skip auth for health, docs, and OPTIONS preflight
        path = request.url.path
        skip_paths = ["/api/v1/health", "/docs", "/redoc", "/openapi.json"]
        if any(path.startswith(p) for p in skip_paths) or request.method == "OPTIONS":
            return await call_next(request)

        # Validate API key header
        api_key = request.headers.get("X-Tokn-Key", "")
        if api_key != settings.tokn_api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
