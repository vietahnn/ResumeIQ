import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
import redis

from services.shared.config import settings
from services.shared.database import engine
from services.shared.kafka import shared_producer as kafka_producer
from services.api.src.api.v1 import resumes_router


@asynccontextmanager
# Manages startup initialization and graceful shutdown for external connections
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    kafka_producer.start()
    yield
    kafka_producer.stop()


app = FastAPI(
    title="ResumeIQ API Gateway Microservice",
    description="Resume Claim-Check upload, parsing ingestion, and profile management API.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes_router, prefix="/api/v1/resumes", tags=["Resumes"])

webapp_index = project_root / "webapp" / "index.html"
if webapp_index.exists():
    @app.get("/app", tags=["Web App"])
    async def serve_webapp():
        return FileResponse(webapp_index)


@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    return {
        "service": "ResumeIQ API Gateway Microservice",
        "version": "1.0.0",
        "status": "running",
        "webapp": "/app"
    }


@app.get("/health", tags=["Health"])
# Checks and reports health status across database, cache, and message queue connections
async def health_check() -> Dict[str, Any]:
    components: Dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception as exc:
        components["database"] = f"unhealthy: {exc}"

    try:
        r = redis.from_url(settings.REDIS_URL)
        if r.ping():
            components["redis"] = "healthy"
    except Exception as exc:
        components["redis"] = f"unhealthy: {exc}"

    components["kafka_producer"] = "ready" if kafka_producer._producer is not None else "disconnected"

    is_healthy = all("unhealthy" not in v for v in components.values())
    return {
        "status": "healthy" if is_healthy else "degraded",
        "environment": settings.APP_ENV,
        "components": components
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.src.main:app", host="0.0.0.0", port=settings.API_PORT, reload=settings.DEBUG)
