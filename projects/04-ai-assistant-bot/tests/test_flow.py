"""Сквозные тесты: настоящий диалог через aiogram, вместо Telegram — FakeSession."""
from bot.llm import LLMError


async def test_start_says_it_is_ai(client, session):
    await client.send("/start")
    text = session.texts()[-1]
    assert "ИИ-ассистент" in text
    assert "Я не человек" in text
    assert "Лимит: 3" in text
    assert "демо-проект" in text


async def test_question_gets_model_answer(client, session, llm):
    llm.reply = "Мы на улице Примерной, 1."
    await client.send("Где вы находитесь?")
    assert session.texts()[-1] == "Мы на улице Примерной, 1."


async def test_operator_and_unknown_command(client, session):
    await client.send("/operator")
    assert "@operator_test" in session.texts()[-1]
    await client.send("/foobar")
    assert "Не знаю такой команды" in session.texts()[-1]


async def test_limit_message_after_daily_limit(client, session, settings):
    for _ in range(settings.daily_limit):
        await client.send("вопрос")
    await client.send("ещё вопрос")
    assert "лимит" in session.texts()[-1]
    assert "@operator_test" in session.texts()[-1]


async def test_too_long_message_is_rejected_and_not_counted(client, session, assistant, settings):
    await client.send("а" * (settings.max_question_chars + 1))
    assert "слишком длинное" in session.texts()[-1]
    assert await assistant.remaining(500) == settings.daily_limit


async def test_reset_command(client, session, storage):
    await client.send("вопрос")
    assert await storage.history(500, 10)
    await client.send("/reset")
    assert await storage.history(500, 10) == []
    assert "забыл" in session.texts()[-1]


async def test_non_text_message(client, session):
    await client.send(None, photo=[{"file_id": "x", "file_unique_id": "y", "width": 1, "height": 1}])
    assert "только текстовые" in session.texts()[-1]


async def test_model_failure_gives_friendly_message(client, session, llm, assistant):
    async def broken(messages, chunks):
        raise LLMError("401 Unauthorized")

    llm.generate = broken
    await client.send("вопрос")
    answer = session.texts()[-1]
    assert "не получается ответить" in answer
    assert "401" not in answer  # технические детали клиенту не показываем
