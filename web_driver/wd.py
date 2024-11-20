import os
import time
import threading
import undetected_chromedriver as uc

from datetime import datetime, timedelta, timezone

from seleniumwire import webdriver
from sqlalchemy.exc import IntegrityError
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from database.models import Connect
from database.db import DbConnection
from email_api import YandexMailClient

TIME_AWAIT = 5


class WebDriver:
    def __init__(self, connect_info: Connect, user: str, db_conn: DbConnection, marketplace: str):

        self.user = user
        self.db_conn = db_conn
        self.mail = connect_info.mail
        self.phone = connect_info.phone
        self.token = connect_info.token
        self.browser_id = f"{connect_info.phone}_{marketplace.lower()}"

        self.marketplaces = self.db_conn.get_marketplaces()

        self.profile_path = os.path.join(os.getcwd(), f"chrome_profile/{self.browser_id}")
        os.makedirs(self.profile_path, exist_ok=True)

        self.proxy_options = {
            'proxy': {
                'http': f'{connect_info.proxy}',
                'https': f'{connect_info.proxy.replace("http", "https")}',
                'no_proxy': 'localhost,127.0.0.1'
            }
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

        self.service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=self.service,
                                       options=self.chrome_options,
                                       seleniumwire_options=self.proxy_options)

        self.monitoring = True

        self.driver.maximize_window()
        self.start_monitoring(interval=1)

    def start_monitoring(self, interval=3.0):
        """Запускает мониторинг вкладок и URL."""

        self.last_url = self.driver.current_url
        self.main_handle = self.driver.current_window_handle

        self.url_monitor_thread = threading.Thread(target=self.monitor_url_changes, args=(interval,), daemon=True)
        # self.tab_monitor_thread = threading.Thread(target=self.monitor_tabs, args=(interval,), daemon=True)

        self.url_monitor_thread.start()
        # self.tab_monitor_thread.start()

    def stop_monitoring(self):
        """Останавливает мониторинг."""
        self.monitoring = False

    def monitor_url_changes(self, interval):
        """Отслеживает изменения URL."""
        while self.monitoring:
            try:
                current_url = self.driver.current_url
                if current_url != self.last_url:
                    print(f"URL изменился на {current_url}, проверка авторизации...")
                    self.check_auth()
                    self.last_url = current_url
            except (NoSuchWindowException, WebDriverException):
                print("Окно браузера закрыто.")
                break
            except Exception as e:
                print(f"Ошибка при мониторинге URL: {e}")
                break
            time.sleep(interval)
        if self.monitoring:
            self.quit()

    def monitor_tabs(self, interval):
        """Отслеживает изменения вкладок."""
        while self.monitoring:
            try:
                all_handles = self.driver.window_handles
                for handle in all_handles:
                    if handle != self.main_handle:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                        self.driver.switch_to.window(self.main_handle)
            except (NoSuchWindowException, WebDriverException):
                print("Окно браузера закрыто.")
                break
            except Exception as e:
                print(f"Ошибка при мониторинге URL: {e}")
                break

            time.sleep(interval)
        if self.monitoring:
            self.quit()

    def check_auth(self):
        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            last_url = None
            while True:
                if last_url == self.driver.current_url:
                    break
                last_url = self.driver.current_url
                WebDriverWait(self.driver, 20).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)
            for marketplace in self.marketplaces:
                if marketplace.link in last_url:
                    self.add_overlay()
                    if marketplace.marketplace == 'Ozon':
                        self.ozon_auth(marketplace)
                    elif marketplace.marketplace == 'WB':
                        self.wb_auth(marketplace)
                    break
            self.remove_overlay()
        except Exception as e:
            self.quit()
            raise e

    def wb_auth(self, marketplace):
        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                input_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR,
                                                                 '.SimpleInput-JIIQvb037j')))
                input_phone.send_keys(self.phone)
                time.sleep(TIME_AWAIT)
                button_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.XPATH,
                                                                 '//*[@data-testid="submit-phone-button"]')))
                break
            except TimeoutException:
                self.driver.refresh()
                self.add_overlay()
        else:
            raise Exception('Страница не получена')

        time_request = datetime.now(tz=timezone(timedelta(hours=3)))
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)
        self.remove_overlay()
        button_phone.click()
        self.add_overlay()

        for _ in range(3):
            try:
                time_request = datetime.now(tz=timezone(timedelta(hours=3)))
                self.db_conn.add_phone_message(user=self.user,
                                               phone=self.phone,
                                               marketplace=marketplace.marketplace,
                                               time_request=time_request)
                break
            except IntegrityError:
                time.sleep(5)
        else:
            raise Exception('Ошибка параллельных запросов')

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)
        try:
            time.sleep(TIME_AWAIT)
            inputs_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.presence_of_all_elements_located((By.CSS_SELECTOR, '.InputCell-PB5beCCt55')))

            if len(mes) == len(inputs_code):
                self.remove_overlay()
                for i, input_code in enumerate(inputs_code):
                    input_code.send_keys(mes[i])
                self.add_overlay()
            else:
                raise Exception('Ошибка ввода кода')
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        for _ in range(10):
            if marketplace.domain in self.driver.current_url:
                break
            time.sleep(5)
        else:
            raise Exception('Вход в ЛК не удался')

    def ozon_auth(self, marketplace):
        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                button_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, '.acn2_47')))
                self.remove_overlay()
                button_mail.click()
                self.add_overlay()
                time.sleep(TIME_AWAIT)
                input_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, '.d018-a')))
                input_mail.send_keys(self.mail)
                time.sleep(TIME_AWAIT)
                button_push = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, '.b2120-b5')))
                break
            except TimeoutException:
                self.driver.refresh()
                self.add_overlay()
        else:
            raise Exception('Страница не получена')

        time_request = datetime.now(tz=timezone(timedelta(hours=3)))
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)
        self.remove_overlay()
        button_push.click()
        self.add_overlay()

        for _ in range(3):
            try:
                time_request = datetime.now(tz=timezone(timedelta(hours=3)))
                self.db_conn.add_phone_message(user=self.user,
                                               phone=self.phone,
                                               marketplace=marketplace.marketplace,
                                               time_request=time_request)
                break
            except IntegrityError:
                time.sleep(5)
        else:
            raise Exception('Ошибка параллельных запросов')

        mail_client = YandexMailClient(mail=self.mail, token=self.token, db_conn=self.db_conn)
        exception = None
        for _ in range(20):
            try:
                mail_client.connect()
                mail_client.fetch_emails(user=self.user, phone=self.phone, time_request=time_request)
                break
            except Exception as e:
                time.sleep(5)
                exception = e
                continue
            finally:
                mail_client.close()
        else:
            raise Exception(exception)

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)
        try:
            time.sleep(TIME_AWAIT)
            input_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, '.d018-a')))

            self.remove_overlay()
            input_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                button_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, '.b2120-b5')))
                break
            except TimeoutException:
                if marketplace.domain in self.driver.current_url:
                    return
        else:
            raise Exception('Вход в ЛК не удался')

        self.remove_overlay()
        button_phone.click()
        self.add_overlay()

        for _ in range(3):
            try:
                time_request = datetime.now(tz=timezone(timedelta(hours=3)))
                self.db_conn.add_phone_message(user=self.user,
                                               phone=self.phone,
                                               marketplace=marketplace.marketplace,
                                               time_request=time_request)
                break
            except IntegrityError:
                time.sleep(5)
        else:
            raise Exception('Ошибка параллельных запросов')

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)
        try:
            time.sleep(TIME_AWAIT)
            input_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, '.d018-a')))

            self.remove_overlay()
            input_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        for _ in range(10):
            if marketplace.link != self.driver.current_url and self.driver.current_url in marketplace.link:
                self.driver.get(marketplace.domain)
                break
            time.sleep(5)
        else:
            raise Exception('Вход в ЛК не удался')

    def add_overlay(self):
        self.driver.execute_script("""
            if (!document.getElementById('block-overlay')) {
                let overlay = document.createElement('div');
                overlay.id = 'block-overlay';
                Object.assign(overlay.style, {
                    position: 'fixed',
                    top: '0',
                    left: '0',
                    width: '100%',
                    height: '100%',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    zIndex: '10000',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '24px',
                    fontFamily: 'Arial, sans-serif'
                });
                overlay.innerText = 'Please wait...';
                document.body.appendChild(overlay);
            }
        """)

    def remove_overlay(self):
        self.driver.execute_script("""
            let overlay = document.getElementById('block-overlay');
            if (overlay) overlay.remove();
        """)

    def is_browser_active(self):
        try:
            if self.driver.session_id is None:
                return False
            if not self.driver.service.is_connectable():
                return False
            return bool(self.driver.current_url)
        except (NoSuchWindowException, InvalidSessionIdException, WebDriverException):
            return False

    def load_url(self, url: str):
        self.driver.get(url)
        self.add_overlay()

    def quit(self):
        """Останавливает мониторинг и закрывает браузер."""
        self.monitoring = False

        self.driver.quit()
