import os
import sys
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.shared.config import settings
from services.shared.kafka import shared_producer
from services.shared.redis import close_redis
from services.bot.src.api.v1.chat import router as chat_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BotAgentService")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ResumeIQ Bot Agent service on port %d...", settings.BOT_PORT)
    shared_producer.start()
    yield
    logger.info("Shutting down ResumeIQ Bot Agent service...")
    shared_producer.stop()
    await close_redis()


app = FastAPI(
    title="ResumeIQ Bot Agent Microservice",
    description="Dedicated microservice for real-time WebSocket conversational RAG and Kafka task dispatching.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounts the chat routes at the root and under /api/v1/chat for flexible client access
app.include_router(chat_router, prefix="")
app.include_router(chat_router, prefix="/api/v1/chat")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "bot-agent",
        "port": settings.BOT_PORT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.bot.src.main:app", host="0.0.0.0", port=settings.BOT_PORT, reload=settings.DEBUG)
