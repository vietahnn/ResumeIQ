import logging
from typing import Optional, Type, TypeVar, AsyncIterator, List
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel

from services.shared.llm.factory import get_chat_model
from services.shared.llm.langfuse_callback import get_langfuse_callback

logger = logging.getLogger("LLMService")

T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self, chat_model: Optional[BaseChatModel] = None):
        self._chat_model = chat_model

    @property
    def model(self) -> BaseChatModel:
        if self._chat_model is None:
            self._chat_model = get_chat_model()
        return self._chat_model

    # Executes asynchronous message invocation returning complete text content
    async def ainvoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        callbacks: Optional[list] = None
    ) -> str:
        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        effective_callbacks = callbacks
        if effective_callbacks is None:
            cb = get_langfuse_callback(trace_name="llm_ainvoke")
            if cb:
                effective_callbacks = [cb]

        config = {"callbacks": effective_callbacks} if effective_callbacks else None
        response = await self.model.ainvoke(messages, config=config)
        return str(response.content)

    # Streams tokens asynchronously from the underlying chat model
    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        callbacks: Optional[list] = None
    ) -> AsyncIterator[str]:
        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        effective_callbacks = callbacks
        if effective_callbacks is None:
            cb = get_langfuse_callback(trace_name="llm_astream")
            if cb:
                effective_callbacks = [cb]

        config = {"callbacks": effective_callbacks} if effective_callbacks else None
        async for chunk in self.model.astream(messages, config=config):
            if chunk.content:
                yield str(chunk.content)

    # Enforces structured response parsing matching a specified Pydantic schema
    async def ainvoke_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        callbacks: Optional[list] = None,
        trace_name: Optional[str] = None
    ) -> T:
        structured_llm = self.model.with_structured_output(schema)
        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        effective_callbacks = callbacks
        if effective_callbacks is None:
            cb = get_langfuse_callback(trace_name=trace_name or f"structured_{schema.__name__}")
            if cb:
                effective_callbacks = [cb]

        config = {"callbacks": effective_callbacks} if effective_callbacks else None
        result = await structured_llm.ainvoke(messages, config=config)
        return result


llm_service = LLMService()
