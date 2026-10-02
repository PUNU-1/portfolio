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

[ -f .env ] || cp .env.example .env

echo "Магазин запускается. Откройте в браузере адрес, который появится ниже."
python -m app.server
