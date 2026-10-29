from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.logging import logger
from app.api.v1.health import router as health_router
from app.api.v1.pipelines import router as pipelines_router
from app.api.v1.runs import router as runs_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.quality import router as quality_router
from app.api.v1.recovery import router as recovery_router
from app.api.v1.metrics import router as metrics_router

app = FastAPI(
    title="Self-Healing Data Pipeline Platform API",
    description="Production-grade autonomous data engineering platform with proactive quality gates, automated healing, and full operational telemetry.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    return response


# Include Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(pipelines_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(quality_router, prefix="/api/v1")
app.include_router(recovery_router, prefix="/api/v1")
app.include_router(metrics_router)  # /metrics at root for Prometheus


@app.get("/")
def root():
    return {
        "message": "Self-Healing Data Pipeline Platform API is active.",
        "docs": "/docs",
        "health": "/api/v1/health",
        "metrics": "/metrics"
    }

