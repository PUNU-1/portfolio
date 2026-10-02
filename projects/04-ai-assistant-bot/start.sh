#!/usr/bin/env bash
# Запуск: bash start.sh
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Первый запуск: создаю виртуальное окружение..."
    python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Создан файл .env. Откройте его, впишите BOT_TOKEN и запустите start.sh снова."
    echo "По умолчанию включён режим без ИИ-модели: чтобы подключить модель, см. README."
    exit 0
fi

python -m bot.main
