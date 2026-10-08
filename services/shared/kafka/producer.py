import asyncio
import json
from typing import Any, Dict, Union, Optional
from confluent_kafka import Producer
from pydantic import BaseModel
from services.shared.config import settings


class KafkaProducerService:
    def __init__(self, client_id: str = "resumeiq-producer"):
        self._producer: Optional[Producer] = None
        self._conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": client_id
        }

    def start(self) -> None:
        if self._producer is None:
            self._producer = Producer(self._conf)

    def stop(self) -> None:
        if self._producer is not None:
            self._producer.flush(timeout=5.0)
            self._producer = None

    # Serializes and publishes an event payload to a Kafka topic in a thread-safe executor
    async def send_event(self, topic: str, event_data: Union[Dict[str, Any], BaseModel]) -> Dict[str, Any]:
        if self._producer is None:
            self.start()

        payload = event_data.model_dump() if isinstance(event_data, BaseModel) else event_data
        payload_bytes = json.dumps(payload, default=str).encode("utf-8")

        def _produce_and_flush() -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            error_holder: list[Exception] = []

            def delivery_callback(err, msg):
                if err is not None:
                    error_holder.append(RuntimeError(f"Kafka delivery failed: {err}"))
                else:
                    result["topic"] = msg.topic()
                    result["partition"] = msg.partition()
                    result["offset"] = msg.offset()

            self._producer.produce(topic=topic, value=payload_bytes, on_delivery=delivery_callback)
            self._producer.flush(timeout=5.0)

            if error_holder:
                raise error_holder[0]
            return result

        return await asyncio.to_thread(_produce_and_flush)


shared_producer = KafkaProducerService()
