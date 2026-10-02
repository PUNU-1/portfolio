@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

if not exist .venv (
    echo Первый запуск: создаю виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo Не удалось создать окружение. Установлен ли Python 3.10+ ?
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Не удалось установить зависимости.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env >nul
    echo Создан файл .env. Откройте его, впишите BOT_TOKEN и запустите start.bat снова.
    echo По умолчанию включён режим без ИИ-модели: чтобы подключить модель, см. README.
    pause
    exit /b 0
)

python -m bot.main
pause
