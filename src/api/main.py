"""
TechSift AI - FastAPI Application Entry Point.
Production-style, zero-cost AI technical document analysis platform.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.v1.endpoints.health import HealthResponse
from src.api.v1.router import api_v1_router
from src.core.config import settings
from src.core.exceptions import AppException
from src.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle event handler verifying database connectivity on startup
    and reconciling interrupted in-flight jobs from prior server sessions.
    Alembic migrations remain the single source of truth for schema management.
    """
    from datetime import datetime, timezone
    from sqlalchemy import text
    from src.db.session import async_engine, async_session_maker
    from src.services.recovery_service import reconcile_interrupted_jobs

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(
            f"Database connectivity check: {exc}. Ensure 'alembic upgrade head' was run."
        )

    # Startup job reconciliation (Single-process architecture)
    startup_time = datetime.now(timezone.utc)
    try:
        async with async_session_maker() as session:
            stats = await reconcile_interrupted_jobs(session, startup_cutoff=startup_time)
            if any(stats.values()):
                logger.info(f"Reconciled interrupted background jobs on startup: {stats}")
    except Exception as exc:
        logger.error(f"Failed to reconcile background jobs on startup: {exc}")

    # Startup system tool verification (ffmpeg / ffprobe for Audio Studio)
    import shutil
    has_ffmpeg = shutil.which("ffmpeg") is not None
    has_ffprobe = shutil.which("ffprobe") is not None
    if not (has_ffmpeg and has_ffprobe):
        logger.warning(
            "System audio tools (ffmpeg/ffprobe) not found on PATH. "
            "Audio narration and podcast stitching require ffmpeg. "
            "Installation instructions: macOS: 'brew install ffmpeg' | "
            "Ubuntu/Debian: 'sudo apt install ffmpeg' | Windows: 'winget install Gyan.FFmpeg'"
        )
    else:
        logger.info("System audio tools verified: ffmpeg and ffprobe are available.")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Zero-cost, production-style AI-powered technical document analysis platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles domain-level application errors with structured JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                details=exc.errors(),
            ),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches unhandled errors.
    Prevents raw tracebacks and internal system paths from being exposed to clients.
    """
    logger.exception(f"Unhandled server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
                details=None,
            ),
        ).model_dump(),
    )


# Root health endpoint (Phase 0 compatibility)
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root Health Check",
)
async def root_health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


# Mount API v1 router
app.include_router(api_v1_router)
