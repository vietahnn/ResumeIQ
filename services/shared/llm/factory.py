import logging
from typing import Optional
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from services.shared.config import settings

logger = logging.getLogger("LLMFactory")


# Factory creating unified LangChain BaseChatModel instances across providers
def get_chat_model(
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    streaming: bool = True
) -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()
    selected_model = model_name or settings.GROQ_MODEL

    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY must be configured in .env for provider 'groq'")

        return init_chat_model(
            model=selected_model,
            model_provider="groq",
            api_key=settings.GROQ_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming
        )

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be configured in .env for provider 'openai'")
        return init_chat_model(
            model=model_name or "gpt-4o-mini",
            model_provider="openai",
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming
        )

    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be configured in .env for provider 'gemini'")
        return init_chat_model(
            model=model_name or "gemini-1.5-flash",
            model_provider="google_genai",
            api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming
        )

    raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported providers: groq, openai, gemini.")
