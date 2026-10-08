import logging
from typing import Optional, List
from services.shared.config import settings

logger = logging.getLogger("LangfuseCallback")


# Creates a LangChain-compatible CallbackHandler for Langfuse Cloud tracing
def get_langfuse_callback(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    trace_name: Optional[str] = None
):
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return None

    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            session_id=session_id,
            user_id=user_id,
            tags=tags or ["resumeiq"],
            trace_name=trace_name
        )
    except ImportError:
        logger.debug("langfuse package not installed. Skipping LLM tracing.")
        return None
    except Exception as exc:
        logger.warning("Could not initialize Langfuse callback: %s", exc)
        return None
