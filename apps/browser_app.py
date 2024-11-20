import threading
import pyautogui
import webbrowser

from PyQt5 import QtWidgets, QtGui, QtCore
from selenium.common.exceptions import WebDriverException, NoSuchWindowException, InvalidSessionIdException

from config import ICON_PATH
from web_driver import WebDriver
from database.db import DbConnection


class BrowserApp(QtWidgets.QWidget):
    browser_loaded = QtCore.pyqtSignal(bool)

    def __init__(self, user: str, db_conn: DbConnection):
        super().__init__()
        self.setWindowTitle("MarketBrowser")
        self.user = user

        self.setWindowIcon(QtGui.QIcon(ICON_PATH))

        screen_width, screen_height = pyautogui.size()
        x_position = (screen_width - 400) // 2
        y_position = (screen_height - 100) // 2

        self.setGeometry(x_position, y_position, 400, 100)
        self.web_drivers = []

        self.db_conn = db_conn
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

    def launch_browser_thread(self):
        marketplace = self.marketplace_select.currentText()
        name_company = self.market_select.currentText()

        market = self.db_conn.get_market(marketplace=marketplace, name_company=name_company)

        self.cleanup_inactive_drivers()
        try:
            for driver in self.web_drivers:
                if driver.browser_id == f"{market.connect_info.phone}_{market.marketplace.lower()}":
                    break
            else:
                web_driver = WebDriver(connect_info=market.connect_info,
                                       marketplace=market.marketplace,
                                       user=self.user,
                                       db_conn=self.db_conn)
                self.web_drivers.append(web_driver)
                web_driver.load_url(url=market.marketplace_info.link)
        except NoSuchWindowException:
            pass
        except (WebDriverException, InvalidSessionIdException) as e:
            if 'invalid session id' not in str(e):
                self.browser_loaded.emit(False)
            return
        except Exception as e:
            print(e)

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
        self.cleanup_inactive_drivers()
        for driver in self.web_drivers:
            driver.quit()
        event.accept()
