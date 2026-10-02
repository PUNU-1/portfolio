"""Клиенты языковой модели. Выбор — через LLM_PROVIDER в .env.

openai — любой OpenAI-совместимый API: OpenAI, OpenRouter, DeepSeek, локальная Ollama и т.д.
         Меняются только LLM_BASE_URL, LLM_API_KEY и LLM_MODEL.
mock   — «модель» без нейросети: просто показывает найденный в базе знаний фрагмент.
         Нужна, чтобы бота можно было запустить и показать без ключа и расходов.
"""
from typing import Protocol

from .config import Settings


class LLMError(Exception):
    """Модель не ответила (сеть, ключ, лимиты провайдера и т.п.)."""


class LLMClient(Protocol):
    async def generate(self, messages: list[dict], chunks: list[str]) -> str: ...


class OpenAICompatibleLLM:
    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30, max_retries=2)
        self.model = model

    async def generate(self, messages: list[dict], chunks: list[str]) -> str:
        from openai import OpenAIError

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,  # меньше «фантазии»: ассистент должен держаться базы знаний
                max_tokens=500,
            )
        except OpenAIError as error:
            raise LLMError(str(error)) from error

        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise LLMError("Модель вернула пустой ответ")
        return text


class MockLLM:
    async def generate(self, messages: list[dict], chunks: list[str]) -> str:
        if not chunks:
            return "В базе знаний по этому вопросу ничего не нашлось. Уточните у оператора: /operator"
        return f"[режим без ИИ-модели] Нашёл в базе знаний:\n\n{chunks[0]}"


def create_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLM()
    return OpenAICompatibleLLM(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
