@echo off

call venv\Scripts\activate

if not defined VIRTUAL_ENV (
    echo Ошибка: виртуальное окружение не активировано.
    exit /b 1
)

pyinstaller --onefile --windowed --hidden-import psycopg2 main.py

deactivate
pause
