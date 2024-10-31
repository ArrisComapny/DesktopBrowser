@echo off

call venv\Scripts\activate

if not defined VIRTUAL_ENV (
    echo Ошибка: виртуальное окружение не активировано.
    exit /b 1
)

pyinstaller my.spec

deactivate
pause
