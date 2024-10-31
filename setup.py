import time

from setuptools import setup
import os

APP = ['main.py']  # Замените 'main.py' на основной файл вашего приложения
DATA_FILES = []    # Укажите дополнительные файлы, такие как иконки и конфигурации, если нужны


# Читаем зависимости из requirements.txt и добавляем их в packages
def get_packages():
    packages = []
    if os.path.exists("requirements-mac.txt"):
        with open("requirements-mac.txt", "r") as f:
            for line in f:
                # Берем только название пакета, убирая версии и лишние символы
                package_name = line.strip().split("~=")[0].split("==")[0]
                if package_name and package_name not in ["pyinstaller", "py2app"]:
                    packages.append(package_name)
    print(packages)
    time.sleep(10)
    return packages


OPTIONS = {
    'argv_emulation': True,
    'packages': get_packages(),
    'excludes': ['tkinter'],  # Исключите ненужные модули
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
