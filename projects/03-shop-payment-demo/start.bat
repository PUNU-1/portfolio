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

if not exist .env copy .env.example .env >nul

echo Магазин запускается. Откройте в браузере адрес, который появится ниже.
python -m app.server
pause
