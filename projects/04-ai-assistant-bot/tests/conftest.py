"""Общие заготовки тестов: подставной Telegram и подставная модель — без сети, токена и ключей."""
from datetime import datetime
from pathlib import Path

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message

from bot.app import build_dispatcher
from bot.assistant import Assistant
from bot.config import Settings
from bot.handlers import router
from bot.knowledge import KnowledgeBase
from bot.llm import MockLLM
from bot.storage import Storage

FAKE_TOKEN = "123456789:" + "A" * 35
FAQ_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "faq.txt"


class FakeSession(BaseSession):
    """Вместо отправки запросов в Telegram запоминает их в self.calls."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):  # не используется
        yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=len(self.calls), date=datetime.now(), chat=Chat(id=method.chat_id, type="private"), text=method.text)
        return True

    def texts(self) -> list[str]:
        return [call.text for call in self.calls if isinstance(call, SendMessage)]


class RecordingLLM:
    """Подставная «модель»: запоминает, что ей отправили, и отвечает заранее заданной фразой."""

    def __init__(self, reply: str = "Ответ модели"):
        self.reply = reply
        self.requests: list[list[dict]] = []
        self.chunks: list[list[str]] = []

    async def generate(self, messages, chunks):
        self.requests.append(messages)
        self.chunks.append(chunks)
        return self.reply


class Client:
    """Имитирует человека, который пишет боту."""

    def __init__(self, dp, bot, user_id: int = 500):
        self.dp, self.bot, self.user_id, self._update_id = dp, bot, user_id, 0

    async def send(self, text: str | None = None, **extra):
        self._update_id += 1
        message = {
            "message_id": self._update_id,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": self.user_id, "type": "private"},
            "from": {"id": self.user_id, "is_bot": False, "first_name": "Тест"},
            **extra,
        }
        if text is not None:
            message["text"] = text
            if text.startswith("/"):
                message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
        await self.dp.feed_raw_update(self.bot, {"update_id": self._update_id, "message": message})


def make_settings(tmp_path, **overrides) -> Settings:
    values = dict(
        bot_token=FAKE_TOKEN,
        llm_provider="mock",
        llm_api_key="",
        llm_base_url="http://unused",
        llm_model="unused",
        company_name="Борода (демо)",
        operator_contact="@operator_test",
        daily_limit=3,
        history_messages=4,
        max_question_chars=200,
        knowledge_file=FAQ_PATH,
        timezone="Europe/Moscow",
        db_path=str(tmp_path / "test.db"),
        demo_notice="Это демо-проект.",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def kb():
    return KnowledgeBase.from_file(FAQ_PATH)


@pytest.fixture
async def storage(settings):
    store = Storage(settings.db_path)
    await store.init()
    return store


@pytest.fixture
def llm():
    return RecordingLLM()


@pytest.fixture
def assistant(settings, kb, storage, llm):
    return Assistant(settings, kb, llm, storage)


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def bot(session):
    return Bot(FAKE_TOKEN, session=session)


@pytest.fixture
def dp(settings, assistant):
    # Роутер в модуле один и тот же, а aiogram позволяет подключить его только к одному Dispatcher.
    # Новый Dispatcher на каждый тест — значит, сначала отсоединяем.
    router._parent_router = None
    return build_dispatcher(settings, assistant)


@pytest.fixture
def client(dp, bot):
    return Client(dp, bot)


@pytest.fixture
def mock_assistant(settings, kb, storage):
    return Assistant(settings, kb, MockLLM(), storage)
