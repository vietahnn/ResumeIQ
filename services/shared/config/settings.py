from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PORT: int = 8000
    BOT_PORT: int = 8001

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_password@localhost:5433/resumeiq_db"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_CHANNEL_PREFIX: str = "channel:session:"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin_password"
    MINIO_BUCKET: str = "resumes"
    MINIO_SECURE: bool = False

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_RESUME_UPLOADED: str = "resume.uploaded"
    KAFKA_TOPIC_RESUME_PROCESSED: str = "resume.processed"
    KAFKA_TOPIC_ANALYSIS_EVENTS: str = "analysis.events"
    KAFKA_TOPIC_NOTIFY_EVENTS: str = "notify.events"
    KAFKA_TOPIC_AGENT_TASKS: str = "agent.tasks"

    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DIMENSION: int = 768

    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    RAPIDAPI_KEY: Optional[str] = None
    RAPIDAPI_HOST: str = "jsearch.p.rapidapi.com"
    TAVILY_API_KEY: Optional[str] = None


settings = Settings()
