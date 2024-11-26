import os
import json
import shutil
import sys
import threading
import zipfile

import pyautogui
import requests

from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtGui, QtCore

from log_api import logger
from config import ICON_PATH, VERSION
from .browser_app import BrowserApp
from database.db import DbConnection


def download_update(url: str):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open("update.zip", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(description="Обновление успешно загружено.")
        return True
    except requests.RequestException as e:
        logger.error(description=f"Ошибка при загрузке обновления: {e}")
        return False


def install_update():
    zip_path = os.path.join(os.getcwd(), "update.zip")
    try:
        if not os.path.exists(zip_path):
            logger.error(description=f"Ошибка: файл {zip_path} не найден.")
            return False

        if not zipfile.is_zipfile(zip_path):
            logger.error(description=f"Ошибка: файл {zip_path} не является ZIP-архивом.")
            return False

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall("update_temp")

        for item in os.listdir("update_temp"):
            src = os.path.join("update_temp", item)
            dest = os.path.join(os.getcwd(), item)
            if os.path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

        shutil.rmtree("update_temp")
        os.remove(zip_path)
        logger.info(description="Обновление установлено успешно.")
        return True

    except zipfile.BadZipFile as e:
        logger.error(description=f"Ошибка: ZIP-архив повреждён: {e}")
        return False

    except FileNotFoundError as e:
        logger.error(description=f"Ошибка: файл не найден: {e}")
        return False

    except PermissionError as e:
        logger.error(description=f"Ошибка: недостаточно прав для доступа к файлу: {e}")
        return False

    except Exception as e:
        logger.error(description=f"Непредвиденная ошибка при установке обновления: {e}")
        return False


def restart_program():
    python = sys.executable
    os.execl(python, python, *sys.argv)


class LoginWorker(QtCore.QThread):
    login_checked = QtCore.pyqtSignal(bool, str, str, str)

    def __init__(self, db_conn, login, password):
        super().__init__()
        self.db_conn = db_conn
        self.login = login
        self.password = password

    def run(self):
        group = self.db_conn.check_user(login=self.login, password=self.password)
        self.login_checked.emit(group is not None, self.login, self.password, group)


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")

        self.setWindowIcon(QtGui.QIcon(ICON_PATH))

        self.credentials_file = 'credentials.json'
        self.db_conn = None
        self.version = None
        self.key = None

        screen_width, screen_height = pyautogui.size()
        x_position = (screen_width - 300) // 2
        y_position = (screen_height - 100) // 2
        self.setGeometry(x_position, y_position, 300, 100)

        self.init_ui()

        threading.Thread(target=self.connect_to_db, daemon=True).start()

    def init_ui(self):
        form_layout = QtWidgets.QFormLayout()

        self.login_input = QtWidgets.QLineEdit(self)
        self.password_input = QtWidgets.QLineEdit(self)
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        form_layout.addRow("Логин:", self.login_input)
        form_layout.addRow("Пароль:", self.password_input)

        self.remember_me_checkbox = QtWidgets.QCheckBox("Запомнить", self)

        self.login_button = QtWidgets.QPushButton("Подключение...", self)
        self.login_button.clicked.connect(self.check_login)
        self.login_button.setEnabled(False)

        self.login_button.setDefault(True)

        self.login_input.returnPressed.connect(self.login_button.click)
        self.password_input.returnPressed.connect(self.login_button.click)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.remember_me_checkbox)
        main_layout.addWidget(self.login_button)

        self.setLayout(main_layout)

    def connect_to_db(self):
        try:
            self.db_conn = DbConnection()
            self.key = self.db_conn.get_key()
            # version = self.db_conn.get_version()
            # if version.version != VERSION:
            #     if download_update(url=version.url) and install_update():
            #         restart_program()
            self.load_credentials()
            self.login_button.setText("Войти")
            self.login_button.setEnabled(True)

        except Exception as e:
            logger.error(description=f"Не удалось подключиться к БД. {str(e)}")
            self.loading_dialog.close()
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к БД.")
            self.close()

    def check_login(self):
        self.login_button.setText("Проверка...")
        self.login_button.setEnabled(False)

        login = self.login_input.text()
        password = self.password_input.text()
        self.worker = LoginWorker(self.db_conn, login, password)
        self.worker.login_checked.connect(self.update_ui_after_login)
        self.worker.start()

    def update_ui_after_login(self, is_valid_user, login, password, group):
        self.login_button.setText("Войти")
        self.login_button.setEnabled(True)

        if is_valid_user:
            logger.info(user=login, description="Вход в приложение")
            if self.remember_me_checkbox.isChecked():
                self.save_credentials(login, password)
            self.open_browser_app(login, group)
        else:
            logger.waring(description=f"Неудачная попытка входа в приложение. Логин: {login} Пароль: {password}")
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неправильный логин или пароль")

    def open_browser_app(self, login: str, group: str):
        self.browser_app = BrowserApp(user=login, group=group, db_conn=self.db_conn)
        self.browser_app.show()
        self.close()

    def save_credentials(self, login, password):
        fernet = Fernet(self.key)
        credentials = {
            "login": fernet.encrypt(login.encode()).decode(),
            "password": fernet.encrypt(password.encode()).decode()
        }
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f)

    def load_credentials(self):
        if os.path.exists(self.credentials_file):
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
                fernet = Fernet(self.key)
                login = fernet.decrypt(credentials.get("login", "").encode()).decode()
                password = fernet.decrypt(credentials.get("password", "").encode()).decode()
                self.login_input.setText(login)
                self.password_input.setText(password)
