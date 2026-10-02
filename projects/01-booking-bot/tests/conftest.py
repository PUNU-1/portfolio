"""Общие заготовки тестов: подставной Telegram, чтобы гонять диалог без сети и токена."""
from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, Message

from bot.app import build_dispatcher
from bot.config import Settings, load_business
from bot.db import Database
from bot.handlers import routers

OWNER_ID = 111
CLIENT_ID = 222
FAKE_TOKEN = "123456789:" + "A" * 35


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
        if isinstance(method, (SendMessage, EditMessageText)):
            chat_id = getattr(method, "chat_id", None) or 1
            return Message(message_id=len(self.calls), date=datetime.now(), chat=Chat(id=chat_id, type="private"), text=method.text)
        return True

    def sent_texts(self, to_chat: int | None = None) -> list[str]:
        """Тексты всех отправленных/изменённых сообщений (опционально — только в один чат)."""
        result = []
        for call in self.calls:
            if isinstance(call, SendMessage) and (to_chat is None or call.chat_id == to_chat):
                result.append(call.text)
            elif isinstance(call, EditMessageText) and to_chat is None:
                result.append(call.text)
        return result


class Client:
    """Имитирует нажатия клиента: отправляет боту «сырые» обновления Telegram."""

    def __init__(self, dp, bot, user_id: int = CLIENT_ID, name: str = "Иван"):
        self.dp, self.bot, self.user_id, self.name = dp, bot, user_id, name
        self._update_id = 0

    def _user(self):
        return {"id": self.user_id, "is_bot": False, "first_name": self.name, "username": "ivan_test"}

    def _chat(self):
        return {"id": self.user_id, "type": "private"}

    async def send(self, text: str):
        self._update_id += 1
        entities = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}] if text.startswith("/") else []
        update = {
            "update_id": self._update_id,
            "message": {
                "message_id": self._update_id,
                "date": int(datetime.now().timestamp()),
                "chat": self._chat(),
                "from": self._user(),
                "text": text,
                "entities": entities,
            },
        }
        await self.dp.feed_raw_update(self.bot, update)

    async def press(self, data: str):
        self._update_id += 1
        update = {
            "update_id": self._update_id,
            "callback_query": {
                "id": str(self._update_id),
                "from": self._user(),
                "chat_instance": "test",
                "data": data,
                "message": {
                    "message_id": 1,
                    "date": int(datetime.now().timestamp()),
                    "chat": self._chat(),
                    "from": {"id": 1, "is_bot": True, "first_name": "bot"},
                    "text": "старое сообщение",
                },
            },
        }
        await self.dp.feed_raw_update(self.bot, update)


@pytest.fixture
def business():
    return load_business()


@pytest.fixture
def settings(tmp_path):
    return Settings(
        bot_token=FAKE_TOKEN,
        owner_id=OWNER_ID,
        admin_ids=frozenset({OWNER_ID}),
        db_path=str(tmp_path / "test.db"),
    )


@pytest.fixture
async def db(settings):
    database = Database(settings.db_path)
    await database.init()
    return database


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def bot(session):
    return Bot(FAKE_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


@pytest.fixture
def dp(settings, business, db):
    # Роутеры в модулях общие, а aiogram разрешает подключить роутер только к одному Dispatcher.
    # Новый Dispatcher на каждый тест — значит, роутеры надо сначала отсоединить.
    for router in routers:
        router._parent_router = None
    return build_dispatcher(settings, business, db)


@pytest.fixture
def client(dp, bot):
    return Client(dp, bot)
