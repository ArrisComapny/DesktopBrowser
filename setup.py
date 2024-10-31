import time

from setuptools import setup
import os

APP = ['main.py']  # Замените 'main.py' на основной файл вашего приложения
DATA_FILES = []    # Укажите дополнительные файлы, такие как иконки и конфигурации, если нужны


OPTIONS = {
    'argv_emulation': True,
    'excludes': ['rubicon'],  # Исключите ненужные модули
    'plist': {
        'CFBundleName': 'ProxyBrowser',          # Имя приложения
        'CFBundleDisplayName': 'ProxyBrowser',   # Имя, отображаемое в macOS
        'CFBundleIdentifier': 'com.example.ProxyBrowser',  # Уникальный идентификатор приложения
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0'
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
