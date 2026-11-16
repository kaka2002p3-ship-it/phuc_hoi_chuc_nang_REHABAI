import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.api.rest import router as rest_router
from backend.api.websocket import router as ws_router
from backend.api.chat import router as chat_router
from backend.api.platform import router as platform_router
from backend.api.admin import router as admin_router
from backend.api.doctor import router as doctor_router
from backend.api.notifications import router as notifications_router
from backend.api.deep_breathing import router as deep_breathing_router, ws_router as deep_breathing_ws_router
from backend.core.db import ensure_default_admin
from backend.core.logging_config import setup_logging, get_logger, RequestLogger

# Initialize structured logging
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    human_readable=os.getenv("APP_ENV", "development").lower() != "production",
    log_file=os.getenv("LOG_FILE")  # Optional file output for production
)
logger = get_logger("rehabai.http")

# Initialize model loader early for health check
try:
    from backend.core.model_loader import model_loader
    model_loader_ready = True
    logger.info("Model loader initialized successfully")
except Exception as e:
    model_loader_ready = False
    logger.error(f"Model loader failed to initialize: {e}", extra={"error": str(e)})

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    logger.info("Starting RehabAI Backend", extra={"version": "1.0.0", "env": os.getenv("APP_ENV", "development")})
    ensure_default_admin()
    yield
    logger.info("Shutting down RehabAI Backend")

app = FastAPI(
    title="RehabAI Backend Inference",
    description="Backend API for real-time RehabAI inference and session management.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for Frontend (Vite/React)
# In production, CORS_ORIGINS must be explicitly configured via environment variable.
# Default development origins:
#   - http://localhost:5173 (Vite dev server)
#   - http://localhost:8080 (Alternative dev server)
#   - http://localhost (Local development)
# Production should list specific frontend domains only.
cors_origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080,http://localhost").split(",") if item.strip()]
if os.getenv("APP_ENV", "development").lower() in {"production", "prod"} and not os.getenv("CORS_ORIGINS", "").strip():
    raise RuntimeError("CORS_ORIGINS must be explicitly configured in production")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    """Structured access log and explicit rate-limit integration point."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Policy"] = "gateway"

    # Log structured request data
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_agent": request.headers.get("user-agent", ""),
        }
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    request_id = request.headers.get("x-request-id") or "unknown"
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.",
            "request_id": request_id,
        }
    )

# Include Routers
app.include_router(rest_router, prefix="/api", tags=["REST"])
app.include_router(chat_router, prefix="/api", tags=["Patient companion"])
app.include_router(platform_router, prefix="/api", tags=["Platform"])
app.include_router(admin_router, prefix="/api", tags=["Admin"])
app.include_router(doctor_router, prefix="/api", tags=["Doctor"])
app.include_router(notifications_router, prefix="/api", tags=["Notifications & clinic"])
app.include_router(deep_breathing_router, prefix="/api", tags=["Deep breathing"])
app.include_router(deep_breathing_ws_router, tags=["Deep breathing WebSocket"])
app.include_router(ws_router, tags=["WebSocket"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
