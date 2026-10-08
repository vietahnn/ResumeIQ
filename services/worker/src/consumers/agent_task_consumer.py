import json
import logging
import asyncio
from typing import Optional
from confluent_kafka import Consumer, KafkaError

from services.shared.config import settings
from services.shared.schemas.events import (
    AgentTaskType,
    AgentTaskRequestEvent,
    AgentTaskResultEvent
)
from services.shared.redis import publish_to_session, set_cache
from services.worker.src.tasks import (
    AnalyzerTask,
    CritiqueTask,
    CoachTask,
    ToolsTask,
    MemoryConsolidatorTask
)

logger = logging.getLogger("AgentTaskConsumer")


class AgentTaskConsumer:
    def __init__(self, group_id: str = "resumeiq-agent-worker-group"):
        self.conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True
        }
        self.consumer: Optional[Consumer] = None
        self.running = False

    def start(self):
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe([settings.KAFKA_TOPIC_AGENT_TASKS])
        self.running = True
        logger.info("Subscribed to Kafka topic '%s' with group '%s'", settings.KAFKA_TOPIC_AGENT_TASKS, self.conf["group.id"])

    def stop(self):
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("AgentTaskConsumer closed.")

    # Processes an individual AgentTaskRequestEvent and publishes status and results to Redis Pub/Sub
    async def process_task(self, event_data: dict) -> None:
        try:
            task_event = AgentTaskRequestEvent(**event_data)
        except Exception as parse_err:
            logger.error("Failed to parse AgentTaskRequestEvent: %s", parse_err)
            return

        session_id = task_event.session_id
        task_id = task_event.task_id
        task_type = task_event.task_type

        # Handle silent background memory consolidation (every 20 exchanges)
        if task_type == AgentTaskType.CONSOLIDATE_MEMORY:
            try:
                summary, facts = await MemoryConsolidatorTask.execute(task_event.payload, session_id)
                logger.info("Successfully consolidated memory for session %s (facts: %d)", session_id, len(facts))
            except Exception as cons_err:
                logger.error("Failed memory consolidation for session %s: %s", session_id, cons_err)
            return

        logger.info("Processing task %s (%s) for session %s", task_id, task_type.value, session_id)

        # 1. Notify client that worker is actively processing heavy domain task
        progress_event = AgentTaskResultEvent(
            task_id=task_id,
            session_id=session_id,
            status="PROGRESS",
            task_type=task_type,
            content=f"Worker is analyzing domain task {task_type.value}...",
            metadata={"step": "executing"}
        )
        await publish_to_session(session_id, progress_event.model_dump())

        # 2. Execute corresponding domain task
        try:
            if task_type == AgentTaskType.JD_MATCHING:
                content, metadata = await AnalyzerTask.execute(task_event.payload, task_event.resume_id)
            elif task_type == AgentTaskType.ATS_CRITIQUE:
                content, metadata = await CritiqueTask.execute(task_event.payload, task_event.resume_id)
            elif task_type == AgentTaskType.INTERVIEW_PREP:
                content, metadata = await CoachTask.execute(task_event.payload, task_event.resume_id)
            elif task_type == AgentTaskType.JOB_SCOUT:
                content, metadata = await ToolsTask.execute(task_event.payload, task_event.resume_id)
            else:
                content, metadata = f"Task type {task_type.value} is not supported.", {}

            # 3. Cache the successful analysis result in Redis for instant future reuse
            await set_cache(
                resume_id=task_event.resume_id,
                task_type=task_type.value,
                payload=task_event.payload,
                result_data={"content": content, "metadata": metadata}
            )
            logger.info(
                "\n%s\n"
                "💾💾💾 [REDIS CACHE SAVED] Analysis outcome cached for 7 days! 💾💾💾\n"
                "   • Task Type : %s\n"
                "   • Resume ID : %s\n"
                "%s",
                "=" * 60,
                task_type.value,
                task_event.resume_id,
                "=" * 60
            )

            # 4. Publish final successful outcome to Redis Pub/Sub
            result_event = AgentTaskResultEvent(
                task_id=task_id,
                session_id=session_id,
                status="SUCCESS",
                task_type=task_type,
                content=content,
                metadata=metadata
            )
            await publish_to_session(session_id, result_event.model_dump())
            logger.info("Successfully executed and published task %s for session %s", task_id, session_id)

        except Exception as exc:
            logger.error("Task execution error for %s: %s", task_id, exc)
            fail_event = AgentTaskResultEvent(
                task_id=task_id,
                session_id=session_id,
                status="FAILED",
                task_type=task_type,
                content=f"An error occurred during task analysis: {str(exc)}",
                metadata={"error": str(exc)}
            )
            await publish_to_session(session_id, fail_event.model_dump())

    # Runs the continuous Kafka polling loop in an async executor
    async def run(self):
        self.start()
        loop = asyncio.get_running_loop()

        while self.running:
            try:
                msg = await loop.run_in_executor(None, self.consumer.poll, 1.0)
                if msg is None:
                    await asyncio.sleep(0.1)
                    continue

                if msg.error():
                    if msg.error().code() in (KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART):
                        continue
                    logger.error("Kafka error: %s", msg.error())
                    continue

                event_data = json.loads(msg.value().decode("utf-8"))
                await self.process_task(event_data)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in AgentTaskConsumer loop: %s", e)
                await asyncio.sleep(1.0)

        self.stop()
