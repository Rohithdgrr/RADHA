from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.core.logging import setup_logging
from app.db.base import Base, engine

setup_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # sqlite file: create tables if not exists (alembic is canonical, but lifespan ensures dev without alembic still works)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("db tables ensured")
    except Exception as e:
        log.warning("db ensure failed", error=str(e))
    yield


app = FastAPI(
    title="AI Council API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — only frontend origin per constitution-check.md C-01/C-02
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import health as health_router  # noqa: E402
from app.routers import models as models_router  # noqa: E402
from app.routers import council as council_router  # noqa: E402
# No website login: only LMArena login is required. Auth router kept for optional private deploy but disabled by default.
# To enable, uncomment:
# from app.auth import router as auth_router  # noqa: E402
# app.include_router(auth_router.router, prefix="/auth", tags=["auth"])

app.include_router(health_router.router, tags=["health"])
app.include_router(models_router.router, tags=["models"])
app.include_router(council_router.router, prefix="/council", tags=["council"])
