import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from confluent_kafka import Consumer, Producer, KafkaError, Message
from sqlalchemy import update

from services.shared.config import settings
from services.shared.database import async_session_factory, Resume, ResumeStatus
from services.shared.storage import minio_storage
from services.worker.src.tasks import DocumentParser, ProfileExtractor, ResumeEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ResumeConsumer")


class ResumeConsumer:
    def __init__(self):
        self._conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "resumeiq-worker-group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False
        }
        self._consumer: Optional[Consumer] = None
        self._producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
        self._running = False

    def start(self) -> None:
        self._consumer = Consumer(self._conf)
        self._consumer.subscribe([settings.KAFKA_TOPIC_RESUME_UPLOADED])
        self._running = True
        logger.info(f"Worker subscribed to topic '{settings.KAFKA_TOPIC_RESUME_UPLOADED}'. Listening for events...")

        try:
            while self._running:
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() in (KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART):
                        continue
                    logger.error(f"Kafka consumer error: {msg.error()}")
                    continue

                self.process_message(msg)
        finally:
            self.stop()

    # Parses document, extracts profile, upserts vector embeddings into Qdrant, updates DB, and emits event
    def process_message(self, msg: Message) -> None:
        payload = {}
        try:
            payload = json.loads(msg.value().decode("utf-8"))
            resume_id = payload.get("resume_id")
            file_path = payload.get("file_path")
            file_name = payload.get("file_name")

            logger.info(f"[Processing Started] resume_id='{resume_id}', file='{file_name}'")

            file_bytes = minio_storage.download_bytes(file_path)
            raw_text = DocumentParser.parse(file_bytes, file_name)
            parsed_data = ProfileExtractor.extract(raw_text)

            asyncio.run(self._update_resume_processing(resume_id, raw_text, parsed_data))
            skills_count = parsed_data.get("skills_count", 0)
            logger.info(f"[Profile Extracted] resume_id='{resume_id}', extracted {skills_count} skills")

            chunks_count = ResumeEmbedder.embed_and_upsert(resume_id, raw_text, parsed_data)
            logger.info(f"[Embedding Complete] resume_id='{resume_id}', stored {chunks_count} vector chunks")

            asyncio.run(self._update_resume_completed(resume_id))
            logger.info(f"[Processing Finished] resume_id='{resume_id}', status='COMPLETED'")

            self._publish_processed_event(resume_id, parsed_data, chunks_count)
            self._consumer.commit(msg)
        except Exception as exc:
            logger.error(f"Failed to process resume: {exc}")
            resume_id = payload.get("resume_id")
            if resume_id:
                asyncio.run(self._update_resume_failed(resume_id, str(exc)))
            self._consumer.commit(msg)

    async def _update_resume_processing(self, resume_id: str, raw_text: str, parsed_data: Dict[str, Any]) -> None:
        async with async_session_factory() as session:
            stmt = (
                update(Resume)
                .where(Resume.id == resume_id)
                .values(
                    raw_text=raw_text,
                    parsed_data=parsed_data,
                    status=ResumeStatus.PROCESSING,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def _update_resume_completed(self, resume_id: str) -> None:
        async with async_session_factory() as session:
            stmt = (
                update(Resume)
                .where(Resume.id == resume_id)
                .values(
                    status=ResumeStatus.COMPLETED,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def _update_resume_failed(self, resume_id: str, error_message: str) -> None:
        async with async_session_factory() as session:
            stmt = (
                update(Resume)
                .where(Resume.id == resume_id)
                .values(
                    status=ResumeStatus.FAILED,
                    error_message=error_message,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()

    def _publish_processed_event(self, resume_id: str, parsed_data: Dict[str, Any], chunks_count: int) -> None:
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": settings.KAFKA_TOPIC_RESUME_PROCESSED,
            "resume_id": resume_id,
            "skills": parsed_data.get("skills", []),
            "chunks_count": chunks_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._producer.produce(
            topic=settings.KAFKA_TOPIC_RESUME_PROCESSED,
            key=resume_id,
            value=json.dumps(event_payload).encode("utf-8")
        )
        self._producer.flush(timeout=3.0)

    def stop(self) -> None:
        self._running = False
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None
            logger.info("Kafka consumer stopped cleanly.")
