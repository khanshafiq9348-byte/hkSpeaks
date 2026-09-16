import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppException, ErrorCode
from app.db.base_class import Base
from app.db.session import engine
from app.db.seed import seed_data
from app.workers.processor import generation_queue

# Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.voices import router as voices_router
from app.api.v1.tts import router as tts_router
from app.api.v1.projects import router as projects_router
from app.api.v1.billing import router as billing_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.admin import router as admin_router
from app.api.v1.storage import router as storage_router
from app.api.v1.health import router as health_router
from app.api.v1.video_editor import router as video_editor_router
from app.api.v1.image_prompts import router as image_prompts_router
from app.api.v1.bulk_images import router as bulk_images_router
from app.workers.video_processor import video_render_queue
from app.workers.prompt_processor import prompt_queue
from app.workers.bulk_image_processor import bulk_image_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts_platform")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist, seed initial data, start worker queues
    logger.info("Initializing database tables and seed data...")
    try:
        await seed_data()
    except Exception as e:
        logger.error(f"Error during seeding: {e}")

    logger.info("Starting background generation queue worker...")
    await generation_queue.start()

    logger.info("Starting background video render queue worker...")
    await video_render_queue.start()

    logger.info("Starting background prompt queue worker...")
    await prompt_queue.start()

    logger.info("Starting background bulk image queue worker...")
    await bulk_image_queue.start()

    yield

    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready AI Text-to-Speech SaaS Platform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "X-Request-ID"]
)

# Request ID & Latency Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id
    start_time = time.time()

    response = await call_next(request)
    
    latency = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time"] = f"{latency}ms"
    return response

# Global Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": req_id
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None)
    raw_errors = exc.errors()
    clean_errors = []
    error_messages = []
    for err in raw_errors:
        loc_parts = [str(l) for l in err.get("loc", []) if l != "body"]
        loc = " -> ".join(loc_parts)
        raw_msg = str(err.get("msg", "Invalid value"))
        msg = raw_msg.replace("Value error, ", "")
        error_messages.append(f"{loc}: {msg}" if loc else msg)
        clean_errors.append({
            "loc": list(err.get("loc", [])),
            "msg": msg,
            "type": str(err.get("type", ""))
        })
    summary_message = "; ".join(error_messages) or "Validation failed"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": summary_message,
                "details": clean_errors
            },
            "detail": clean_errors,
            "request_id": req_id
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    logger.exception(f"Unhandled error processing request {req_id}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "An unexpected internal server error occurred."
            },
            "request_id": req_id
        }
    )

# Register API Routers under /v1
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(voices_router, prefix=settings.API_V1_STR)
app.include_router(tts_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(billing_router, prefix=settings.API_V1_STR)
app.include_router(api_keys_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(storage_router, prefix=settings.API_V1_STR)
app.include_router(video_editor_router, prefix=settings.API_V1_STR)
app.include_router(image_prompts_router, prefix=settings.API_V1_STR)
app.include_router(bulk_images_router, prefix=settings.API_V1_STR)

# Mount Health check at root
app.include_router(health_router)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }
