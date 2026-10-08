import sys
import time
import signal
import asyncio
import threading
import logging
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.shared.config import settings
from services.shared.kafka.admin import ensure_topics_exist
from services.worker.src.consumers import ResumeConsumer, AgentTaskConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("WorkerMain")


# Manages multi-threaded lifecycle for resume processing and agent task consumers
def main() -> None:
    logger.info("=== ResumeIQ Specialized Worker Pool Starting ===")

    # Auto-ensure Kafka topics exist before subscribing consumers
    ensure_topics_exist(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        topics=[settings.KAFKA_TOPIC_RESUME_UPLOADED, settings.KAFKA_TOPIC_AGENT_TASKS]
    )

    resume_consumer = ResumeConsumer()
    agent_task_consumer = AgentTaskConsumer()

    # Worker thread 1: Ingestion & Embedding consumer for uploaded resumes
    resume_thread = threading.Thread(
        target=resume_consumer.start,
        name="ResumeConsumerThread",
        daemon=True
    )

    # Worker thread 2: Analytical AI Agent task consumer (matching, critique, coach, tools)
    def _run_agent_task_consumer():
        asyncio.run(agent_task_consumer.run())

    agent_thread = threading.Thread(
        target=_run_agent_task_consumer,
        name="AgentTaskConsumerThread",
        daemon=True
    )

    def handle_shutdown(signum, frame):
        logger.info("\nShutdown signal received. Gracefully stopping all worker consumers...")
        resume_consumer.stop()
        agent_task_consumer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    resume_thread.start()
    agent_thread.start()

    logger.info("All worker threads successfully launched.")

    while resume_thread.is_alive() and agent_thread.is_alive():
        time.sleep(1)


if __name__ == "__main__":
    main()
