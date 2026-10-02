"""Обработчики сообщений. Все ответы — обычный текст без разметки: ответ модели может содержать любые символы."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .assistant import Assistant, LimitReached
from .config import Settings
from .llm import LLMError

log = logging.getLogger(__name__)
router = Router()


def start_text(settings: Settings) -> str:
    text = (
        f"Здравствуйте! Я ИИ-ассистент компании «{settings.company_name}». "
        "Я не человек, а программа, и могу ошибаться: за важным (цены, запись) "
        "лучше уточнить у оператора — /operator.\n\n"
        "Отвечаю на вопросы по базе знаний компании. Просто напишите, что вас интересует.\n\n"
        f"Лимит: {settings.daily_limit} сообщений в сутки. "
        f"Я помню последние {settings.history_messages} реплик нашего разговора; "
        "забыть их — /reset."
    )
    if settings.demo_notice:
        text += f"\n\n{settings.demo_notice}"
    return text


@router.message(CommandStart())
async def cmd_start(message: Message, settings: Settings) -> None:
    await message.answer(start_text(settings))


@router.message(Command("reset"))
async def cmd_reset(message: Message, assistant: Assistant) -> None:
    await assistant.reset(message.from_user.id)
    await message.answer("Готово, я забыл наш разговор. Лимит сообщений на сегодня при этом не обнуляется.")


@router.message(Command("operator"))
async def cmd_operator(message: Message, settings: Settings) -> None:
    await message.answer(f"Живой оператор: {settings.operator_contact}")


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message) -> None:
    await message.answer("Не знаю такой команды. Просто напишите вопрос обычным текстом или нажмите /start.")


@router.message(F.text)
async def question(message: Message, assistant: Assistant, settings: Settings) -> None:
    text = message.text.strip()
    if len(text) > settings.max_question_chars:
        await message.answer(f"Сообщение слишком длинное. Сократите его до {settings.max_question_chars} символов.")
        return

    user_id = message.from_user.id
    async with assistant.lock_for(user_id):
        await message.bot.send_chat_action(message.chat.id, "typing")
        try:
            answer = await assistant.answer(user_id, text)
        except LimitReached:
            await message.answer(
                f"На сегодня лимит в {settings.daily_limit} сообщений исчерпан. "
                f"Приходите завтра или напишите оператору: {settings.operator_contact}"
            )
            return
        except LLMError as error:
            log.error("Ошибка модели: %s", error)
            await message.answer(
                f"Сейчас не получается ответить, попробуйте позже. Оператор на связи: {settings.operator_contact}"
            )
            return
    await message.answer(answer)


@router.message()
async def non_text(message: Message) -> None:
    await message.answer("Я понимаю только текстовые сообщения. Напишите вопрос словами.")
