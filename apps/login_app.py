import os
import json
import threading
import pyautogui

from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtGui, QtCore

from log_api import logger
from config import ICON_PATH
from .browser_app import BrowserApp
from database.db import DbConnection


class LoginWorker(QtCore.QThread):
    login_checked = QtCore.pyqtSignal(bool, str, str)

    def __init__(self, db_conn, login, password):
        super().__init__()
        self.db_conn = db_conn
        self.login = login
        self.password = password

    def run(self):
        is_valid_user = self.db_conn.check_user(login=self.login, password=self.password)
        self.login_checked.emit(is_valid_user, self.login, self.password)


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")

        self.setWindowIcon(QtGui.QIcon(ICON_PATH))

        self.credentials_file = 'credentials.json'
        self.db_conn = None
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

    def update_ui_after_login(self, is_valid_user, login, password):
        self.login_button.setText("Войти")
        self.login_button.setEnabled(True)

        if is_valid_user:
            logger.info(user=login, description="Вход в приложение")
            if self.remember_me_checkbox.isChecked():
                self.save_credentials(login, password)
            self.open_browser_app(login)
        else:
            logger.waring(description=f"Неудачная попытка входа в приложение. Логин: {login} Пароль: {password}")
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неправильный логин или пароль")

    def open_browser_app(self, login: str):
        self.browser_app = BrowserApp(user=login, db_conn=self.db_conn)
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
