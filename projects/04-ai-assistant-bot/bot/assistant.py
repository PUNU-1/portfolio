"""Логика ассистента: лимит -> поиск по базе знаний -> память диалога -> модель."""
import asyncio
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Settings
from .knowledge import KnowledgeBase
from .llm import LLMClient
from .prompts import build_system_prompt
from .storage import Storage


class LimitReached(Exception):
    """Человек исчерпал дневной лимит сообщений."""


class Assistant:
    def __init__(self, settings: Settings, kb: KnowledgeBase, llm: LLMClient, storage: Storage):
        self.settings = settings
        self.kb = kb
        self.llm = llm
        self.storage = storage
        # На каждого человека — своя «очередь», чтобы быстрыми сообщениями нельзя было обойти лимит
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock_for(self, user_id: int) -> asyncio.Lock:
        return self._locks[user_id]

    def _today(self) -> str:
        return datetime.now(ZoneInfo(self.settings.timezone)).date().isoformat()

    async def remaining(self, user_id: int) -> int:
        used = await self.storage.usage(user_id, self._today())
        return max(0, self.settings.daily_limit - used)

    async def answer(self, user_id: int, question: str) -> str:
        """Возвращает ответ или бросает LimitReached / LLMError."""
        if await self.remaining(user_id) == 0:
            raise LimitReached

        history = await self.storage.history(user_id, self.settings.history_messages)
        chunks = self._find_knowledge(question, history)

        llm_chunks = chunks
        if self.settings.llm_provider == "mock" and not self.kb.search(question):
            # Режим без модели не умеет понимать контекст диалога: если сам вопрос ничего не нашёл,
            # честно говорим «не нашёл», а не цитируем блок от прошлой реплики
            llm_chunks = []

        system_prompt = build_system_prompt(self.settings.company_name, self.settings.operator_contact, chunks)
        messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": question}]
        answer = await self.llm.generate(messages, llm_chunks)

        # Сохраняем только после успешного ответа: при сбое модели лимит и память не тратятся
        keep = self.settings.history_messages
        await self.storage.add_message(user_id, "user", question, keep)
        await self.storage.add_message(user_id, "assistant", answer, keep)
        await self.storage.add_usage(user_id, self._today())
        return answer

    def _find_knowledge(self, question: str, history: list[dict]) -> list[str]:
        """Сначала ищем по самому вопросу, затем добавляем найденное с учётом прошлой реплики.

        Так уточнения вроде «а сколько это стоит?» тоже находят нужный блок.
        """
        chunks = self.kb.search(question)
        previous = [m["content"] for m in history if m["role"] == "user"][-1:]
        if previous:
            for chunk in self.kb.search(f"{previous[0]} {question}"):
                if chunk not in chunks:
                    chunks.append(chunk)
        return chunks[:5]

    async def reset(self, user_id: int) -> None:
        await self.storage.clear_history(user_id)
