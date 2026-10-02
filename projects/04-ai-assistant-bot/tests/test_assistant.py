from dataclasses import replace

import pytest

from bot.assistant import Assistant, LimitReached
from bot.llm import LLMError


async def test_system_prompt_declares_ai_and_contains_knowledge(assistant, llm):
    await assistant.answer(1, "Где вы находитесь?")
    system = llm.requests[0][0]
    assert system["role"] == "system"
    assert "ИИ-ассистент" in system["content"]
    assert "Не выдумывай" in system["content"]
    assert "ул. Примерная, 1" in system["content"]  # найденный фрагмент базы знаний
    assert "@operator_test" in system["content"]


async def test_prompt_says_nothing_found_for_offtopic(assistant, llm):
    await assistant.answer(1, "Какая погода на Марсе?")
    assert "ничего не найдено" in llm.requests[0][0]["content"]


async def test_dialog_memory_is_passed_to_model(assistant, llm):
    await assistant.answer(1, "Сколько стоит детская стрижка?")
    await assistant.answer(1, "А сколько длится?")

    second_request = llm.requests[1]
    roles = [m["role"] for m in second_request]
    assert roles == ["system", "user", "assistant", "user"]
    assert second_request[1]["content"] == "Сколько стоит детская стрижка?"
    assert second_request[-1]["content"] == "А сколько длится?"


async def test_followup_finds_knowledge_using_previous_question(settings, kb, llm, storage):
    with_model = Assistant(replace(settings, llm_provider="openai"), kb, llm, storage)  # у модели есть память диалога
    await with_model.answer(1, "Расскажите про детскую стрижку")
    await with_model.answer(1, "А сколько это длится?")
    # в вопросе-уточнении слова «детская» нет, но блок найден благодаря предыдущей реплике
    assert any("Детская стрижка" in chunk for chunk in llm.chunks[1])


async def test_mock_does_not_reuse_previous_topic_for_offtopic_question(mock_assistant):
    await mock_assistant.answer(1, "Можно ли оплатить по QR?")
    answer = await mock_assistant.answer(1, "Расскажи про погоду на Марсе")
    assert "QR" not in answer
    assert "/operator" in answer


async def test_memory_is_limited(settings, kb, llm, storage):
    roomy = Assistant(replace(settings, daily_limit=50), kb, llm, storage)  # лимит сообщений не мешает
    for i in range(5):
        await roomy.answer(1, f"вопрос номер {i}")
    history = await storage.history(1, 100)
    assert len(history) == settings.history_messages  # хранится не больше N последних реплик
    assert history[-2]["content"] == "вопрос номер 4"


async def test_memory_is_per_user(assistant, storage):
    await assistant.answer(1, "вопрос первого")
    await assistant.answer(2, "вопрос второго")
    assert [m["content"] for m in await storage.history(1, 10) if m["role"] == "user"] == ["вопрос первого"]


async def test_reset_clears_memory_but_not_limit(assistant, storage, settings):
    await assistant.answer(1, "привет")
    await assistant.reset(1)
    assert await storage.history(1, 10) == []
    assert await assistant.remaining(1) == settings.daily_limit - 1


async def test_daily_limit(assistant, settings):
    for _ in range(settings.daily_limit):
        await assistant.answer(1, "вопрос")
    with pytest.raises(LimitReached):
        await assistant.answer(1, "ещё вопрос")
    await assistant.answer(2, "другой человек не затронут")


async def test_failed_model_call_costs_nothing(assistant, llm, settings, storage):
    async def broken(messages, chunks):
        raise LLMError("сеть недоступна")

    llm.generate = broken
    with pytest.raises(LLMError):
        await assistant.answer(1, "вопрос")
    assert await assistant.remaining(1) == settings.daily_limit
    assert await storage.history(1, 10) == []


async def test_mock_llm_quotes_knowledge(mock_assistant):
    answer = await mock_assistant.answer(1, "Какой у вас график работы?")
    assert "режим без ИИ-модели" in answer
    assert "с 10:00 до 20:00" in answer


async def test_mock_llm_offers_operator_when_nothing_found(mock_assistant):
    answer = await mock_assistant.answer(1, "расскажи про погоду на марсе")
    assert "/operator" in answer
