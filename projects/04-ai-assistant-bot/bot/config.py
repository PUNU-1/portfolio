"""Все настройки берём из .env (образец — .env.example)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    bot_token: str
    llm_provider: str  # "openai" (любой OpenAI-совместимый API) или "mock" (без модели)
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    company_name: str
    operator_contact: str
    daily_limit: int  # сколько сообщений в сутки можно написать одному человеку
    history_messages: int  # сколько последних сообщений диалога помнит ассистент
    max_question_chars: int
    knowledge_file: Path
    timezone: str
    db_path: str
    demo_notice: str


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.isdigit() else default


def load_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env")

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "put_your_token_here":
        raise SystemExit(
            "Не задан BOT_TOKEN. Создайте бота у @BotFather и впишите токен в файл .env."
        )

    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider not in ("openai", "mock"):
        raise SystemExit("LLM_PROVIDER должен быть openai или mock.")

    api_key = os.getenv("LLM_API_KEY", "").strip()
    if provider == "openai" and not api_key:
        raise SystemExit(
            "LLM_PROVIDER=openai, но LLM_API_KEY пуст. Впишите ключ в .env "
            "или поставьте LLM_PROVIDER=mock, чтобы попробовать бота без модели."
        )

    knowledge_file = Path(os.getenv("KNOWLEDGE_FILE", "knowledge/faq.txt"))
    if not knowledge_file.is_absolute():
        knowledge_file = BASE_DIR / knowledge_file

    return Settings(
        bot_token=token,
        llm_provider=provider,
        llm_api_key=api_key,
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip(),
        company_name=os.getenv("COMPANY_NAME", "Борода (демо)").strip(),
        operator_contact=os.getenv("OPERATOR_CONTACT", "@your_telegram").strip(),
        daily_limit=_int("DAILY_MESSAGE_LIMIT", 20),
        history_messages=_int("HISTORY_MESSAGES", 10),
        max_question_chars=_int("MAX_QUESTION_CHARS", 800),
        knowledge_file=knowledge_file,
        timezone=os.getenv("TIMEZONE", "Europe/Moscow").strip(),
        db_path=os.getenv("DB_PATH", str(BASE_DIR / "assistant.db")),
        demo_notice=os.getenv(
            "DEMO_NOTICE", "Это демо-проект из портфолио: компания вымышленная, данные ненастоящие."
        ).strip(),
    )
