import logging
from typing import List
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

logger = logging.getLogger("KafkaAdmin")


# Ensures required Kafka topics exist with proper partitions and replication factor
def ensure_topics_exist(bootstrap_servers: str, topics: List[str], num_partitions: int = 3, replication_factor: int = 1) -> None:
    try:
        admin = AdminClient({"bootstrap.servers": bootstrap_servers})
        metadata = admin.list_topics(timeout=10.0)
        existing = set(metadata.topics.keys())

        missing = [t for t in topics if t not in existing]
        if not missing:
            return

        new_topics = [
            NewTopic(t, num_partitions=num_partitions, replication_factor=replication_factor)
            for t in missing
        ]
        futures = admin.create_topics(new_topics)
        for topic, f in futures.items():
            try:
                f.result()
                logger.info("Auto-created missing Kafka topic: '%s'", topic)
            except KafkaException as e:
                # If topic was created concurrently by broker, ignore error
                if "TopicExistsError" not in str(e):
                    logger.warning("Could not auto-create topic '%s': %s", topic, e)
    except Exception as err:
        logger.warning("Kafka topic existence check failed: %s", err)
