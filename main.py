import os
import sys
import json
import threading
import webbrowser

import pyautogui
import undetected_chromedriver as uc

from PyQt5 import QtWidgets, QtGui, QtCore
from seleniumwire import webdriver
from cryptography.fernet import Fernet
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchWindowException, WebDriverException

from database.db import DbConnection

# if hasattr(sys, '_MEIPASS'):
#     icon_path = os.path.join(sys._MEIPASS, 'chrome.png')
# else:
#     icon_path = os.path.join(os.getcwd(), 'chrome.png')


class WebDriver:
    def __init__(self, phone: str, proxy: str):

        self.browser_id = phone

        self.profile_path = os.path.join(os.getcwd(), f"chrome_profile/chrome_profile_{phone}")
        os.makedirs(self.profile_path, exist_ok=True)

        self.proxy_options = {
            'proxy': {
                'http': f'{proxy}',
                'https': f'{proxy.replace("http", "https")}',
                'no_proxy': 'localhost,127.0.0.1'
            },
            'disable_capture': True
        }

        self.chrome_options = uc.ChromeOptions()

        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-automation")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--allow-insecure-localhost")
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument(f"--user-data-dir={self.profile_path}")
        self.chrome_options.add_experimental_option("useAutomationExtension", False)
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                         "(KHTML, like Gecko) Chrome/119.0.5945.86 Safari/537.36")

        try:
            self.service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=self.service,
                                           options=self.chrome_options,
                                           seleniumwire_options=self.proxy_options)
            self.driver.maximize_window()
        except WebDriverException as e:

            raise e

    def is_browser_active(self):
        try:
            return bool(self.driver.current_url)
        except NoSuchWindowException:
            return False

    def open_new_tab(self, url: str):
        try:
            if self.is_browser_active():
                self.driver.execute_script(f"window.open('{url}', '_blank');")
                self.driver.switch_to.window(self.driver.window_handles[-1])
            else:
                self.load_url(url)
        except NoSuchWindowException:
            self.load_url(url)

    def load_url(self, url: str):
        self.driver.get(url)

    def quit(self):
        self.driver.quit()


class BrowserApp(QtWidgets.QWidget):
    browser_loaded = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarketBrowser")

        # self.setWindowIcon(QtGui.QIcon(icon_path))

        screen_width, screen_height = pyautogui.size()
        x_position = (screen_width - 400) // 2
        y_position = (screen_height - 100) // 2

        self.setGeometry(x_position, y_position, 400, 100)
        self.web_drivers = []

        self.db_conn = DbConnection()
        self.markets = self.db_conn.info()

        self.browser_loaded.connect(self.on_browser_loaded)

        self.init_ui()

    def init_ui(self):

        marketplaces = sorted(list({m.marketplace for m in self.markets}))

        self.marketplace_select = QtWidgets.QComboBox()
        self.marketplace_select.addItems(marketplaces)
        self.marketplace_select.currentTextChanged.connect(self.update_markets)

        self.market_select = QtWidgets.QComboBox()
        self.update_markets()

        self.launch_button = QtWidgets.QPushButton("Запуск браузера")
        self.launch_button.clicked.connect(self.launch_browser)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Выберите маркетплейс:", self.marketplace_select)
        form_layout.addRow("Выберите рынок:", self.market_select)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.launch_button)
        self.launch_button.setEnabled(True)

        self.setLayout(layout)

    def update_markets(self):
        selected_marketplace = self.marketplace_select.currentText()

        filtered_companies = sorted([m.name_company for m in self.markets if m.marketplace == selected_marketplace])

        self.market_select.clear()
        self.market_select.addItems(filtered_companies)

    def launch_browser(self):
        self.launch_button.setEnabled(False)
        self.launch_button.setText('Загружаю браузер...')
        threading.Thread(target=self.launch_browser_thread, daemon=True).start()
        # QtCore.QTimer.singleShot(0, self.launch_browser_thread)

    def launch_browser_thread(self):
        marketplace = self.marketplace_select.currentText()
        name_company = self.market_select.currentText()

        market = self.db_conn.get_market(marketplace=marketplace, name_company=name_company)

        self.cleanup_inactive_drivers()

        for driver in self.web_drivers:
            if driver.browser_id == market.connect_info.phone:
                driver.open_new_tab(market.marketplace_info.link)
                break
        else:
            try:
                web_driver = WebDriver(phone=market.connect_info.phone, proxy=market.connect_info.proxy)
                self.web_drivers.append(web_driver)
                web_driver.load_url(market.marketplace_info.link)
            except WebDriverException:
                self.browser_loaded.emit(False)
                return

        self.browser_loaded.emit(True)

    def on_browser_loaded(self, success):
        if not success:
            QtWidgets.QMessageBox.critical(None, "Ошибка", "Не удалось запустить Chrome. Пожалуйста, установите его.")
            webbrowser.open("https://www.google.com/chrome/")
        self.launch_button.setEnabled(True)
        self.launch_button.setText("Запуск браузера")

    def cleanup_inactive_drivers(self):
        self.web_drivers = [driver for driver in self.web_drivers if driver.is_browser_active()]

    def closeEvent(self, event):
        for driver in self.web_drivers:
            driver.quit()
        event.accept()


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

        # self.setWindowIcon(QtGui.QIcon(icon_path))

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
            self.loading_dialog.close()
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к БД: {str(e)}")
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
            if self.remember_me_checkbox.isChecked():
                self.save_credentials(login, password)
            self.open_browser_app()
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неправильный логин или пароль")

    def open_browser_app(self):
        self.browser_app = BrowserApp()
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
