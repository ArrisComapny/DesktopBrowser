#!/bin/bash

git pull origin master

source venv/bin/activate

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Ошибка: виртуальное окружение не активировано."
    exit 1
fi

pyinstaller my.spec

deactivate

read -p "Нажмите любую клавишу для завершения..."