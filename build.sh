#!/bin/bash

git pull origin master

source venv/bin/activate

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Ошибка: виртуальное окружение не активировано."
    exit 1
fi

libc_path=$(find /usr /Library /opt -name "libc++.dylib" 2>/dev/null | head -n 1)

if [[ -z "$libc_path" ]]; then
    echo "Ошибка: библиотека libc++.dylib не найдена."
    exit 1
fi

pyinstaller --paths "$libc_path" my.spec

deactivate

read -p "Нажмите любую клавишу для завершения..."
