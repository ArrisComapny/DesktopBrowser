import os
import time
import undetected_chromedriver as uc

from contextlib import suppress
from seleniumwire import webdriver
from sqlalchemy.exc import IntegrityError
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from database.models import Connect
from database.db import DbConnection
from email_api import YandexMailClient
from log_api import logger, get_moscow_time

TIME_AWAIT = 5


class WebDriver:
    def __init__(self, connect_info: Connect, user: str, auto: bool, db_conn: DbConnection, marketplace: str):

        self.user = user
        self.auto = auto
        self.db_conn = db_conn
        self.mail = connect_info.mail
        self.proxy = connect_info.proxy
        self.phone = connect_info.phone
        self.token = connect_info.token
        self.browser_id = f"{connect_info.phone}_{marketplace.lower()}"

        self.marketplaces = self.db_conn.get_marketplaces()

        self.profile_path = os.path.join(os.getcwd(), f"chrome_profile/{self.browser_id}")
        os.makedirs(self.profile_path, exist_ok=True)

        self.proxy_options = {
            'proxy': {
                'http': f'{self.proxy}',
                'https': f'{self.proxy.replace("http", "https")}',
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
        self.driver.maximize_window()

    def check_auth(self):
        try:
            WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            last_url = None
            while True:
                if last_url == self.driver.current_url:
                    break
                last_url = self.driver.current_url
                WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                time.sleep(4)
            for marketplace in self.marketplaces:
                if marketplace.link in last_url:
                    self.add_overlay()
                    logger.info(user=self.user, proxy=self.proxy,
                                description=f"Автоматизация {marketplace.marketplace} запущена")
                    if marketplace.marketplace == 'Ozon':
                        self.ozon_auth(marketplace)
                    elif marketplace.marketplace == 'WB':
                        self.wb_auth(marketplace)
                    break
                if marketplace.domain in last_url:
                    logger.info(user=self.user, proxy=self.proxy,
                                description=f"Вход в ЛК {marketplace.marketplace} {self.phone} выполнен")
            self.remove_overlay()
        except Exception as e:
            logger.error(user=self.user, proxy=self.proxy,
                         description=f"Ошибка автоматизации. {str(e).splitlines()[0]}")
            self.quit()

    def wb_auth(self, marketplace):
        logger.info(user=self.user, proxy=self.proxy, description=f"Ввод номера {self.phone}")

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

        logger.info(user=self.user, proxy=self.proxy, description=f"Проверка заявки на СМС на номер {self.phone}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)
        self.remove_overlay()
        button_phone.click()
        self.add_overlay()

        logger.info(user=self.user, proxy=self.proxy, description=f"Ожидание кода на номер {self.phone}")

        for _ in range(3):
            try:
                self.db_conn.add_phone_message(user=self.user,
                                               phone=self.phone,
                                               marketplace=marketplace.marketplace,
                                               time_request=time_request)
                break
            except IntegrityError:
                time.sleep(TIME_AWAIT)
        else:
            raise Exception('Ошибка параллельных запросов')

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)

        logger.info(user=self.user, proxy=self.proxy, description=f"Код на номер {self.phone} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"Ввод кода {mes}")

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

        logger.info(user=self.user, proxy=self.proxy, description=f"Вход в ЛК {marketplace.marketplace} {self.phone}")
        for _ in range(10):
            if marketplace.domain in self.driver.current_url:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"Вход в ЛК {marketplace.marketplace} {self.phone} выполнен")
                return
            time.sleep(TIME_AWAIT)

    def ozon_auth(self, marketplace):
        with suppress(TimeoutException):
            h2 = WebDriverWait(self.driver, TIME_AWAIT).until(expected_conditions.presence_of_element_located((
                By.XPATH, "//h2[@qa-id='ozonIdCredentialSettingsTitle']")))
            if h2:
                self.driver.get(marketplace.domain)
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"Вход в ЛК {marketplace.marketplace} {self.phone} выполнен")
                return

        logger.info(user=self.user, proxy=self.proxy, description=f"Ввод почты {self.mail}")
        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                button_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.XPATH, "//div[text()='Войти по почте']")))
                self.remove_overlay()
                button_mail.click()
                self.add_overlay()
                time.sleep(TIME_AWAIT)
                input_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.ID, "email")))
                input_mail.send_keys(Keys.CONTROL, 'a')
                input_mail.send_keys(Keys.DELETE)
                input_mail.send_keys(self.mail)
                time.sleep(TIME_AWAIT)
                button_push = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.XPATH, "//button[.//div[text()='Войти']]")))
                break
            except TimeoutException:
                self.driver.refresh()
                self.add_overlay()
        else:
            raise Exception('Страница не получена')

        logger.info(user=self.user, proxy=self.proxy, description=f"Проверка заявки на Email {self.mail}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)
        self.remove_overlay()
        button_push.click()
        self.add_overlay()

        logger.info(user=self.user, proxy=self.proxy, description=f"Ожидание кода на Email {self.mail}")

        for _ in range(3):
            try:
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
                time.sleep(TIME_AWAIT)
                exception = e
                continue
            finally:
                mail_client.close()
        else:
            raise Exception(exception)

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)

        logger.info(user=self.user, proxy=self.proxy, description=f"Код на Email {self.mail} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"Ввод кода {mes}")

        try:
            time.sleep(TIME_AWAIT)
            input_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "input[type='number']")))

            self.remove_overlay()
            input_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        logger.info(user=self.user, proxy=self.proxy, description=f"Вход в ЛК {marketplace.marketplace} {self.phone}")
        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                button_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.XPATH, "//button[.//div[text()='Войти']]")))
                logger.info(user=self.user, proxy=self.proxy, description=f"Ожидание кода на номер {self.phone}")
                break
            except TimeoutException:
                self.driver.get(marketplace.domain)
                if marketplace.domain in self.driver.current_url:
                    logger.info(user=self.user, proxy=self.proxy,
                                description=f"Вход в ЛК {marketplace.marketplace} {self.phone} выполнен")
                    return
        else:
            return

        logger.info(user=self.user, proxy=self.proxy, description=f"Проверка заявки на СМС на номер {self.phone}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)

        self.remove_overlay()
        button_phone.click()
        self.add_overlay()

        logger.info(user=self.user, proxy=self.proxy, description=f"Ожидание кода на номер {self.phone}")

        for _ in range(3):
            try:
                self.db_conn.add_phone_message(user=self.user,
                                               phone=self.phone,
                                               marketplace=marketplace.marketplace,
                                               time_request=time_request)
                break
            except IntegrityError:
                time.sleep(TIME_AWAIT)
        else:
            raise Exception('Ошибка параллельных запросов')

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)

        logger.info(user=self.user, proxy=self.proxy, description=f"Код на номер {self.phone} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"Ввод кода {mes}")

        try:
            time.sleep(TIME_AWAIT)
            input_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "input[type='number']")))

            self.remove_overlay()
            input_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        logger.info(user=self.user, proxy=self.proxy, description=f"Вход в ЛК {marketplace.marketplace} {self.phone}")
        for _ in range(3):
            self.add_overlay()
            time.sleep(TIME_AWAIT)
            self.driver.get(marketplace.domain)
            if marketplace.domain in self.driver.current_url:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"Ввход в ЛК {marketplace.marketplace} {self.phone} выполнен")
                return

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
        if self.auto:
            logger.info(user=self.user, proxy=self.proxy, description=f"Авторизация на {url}")
            self.driver.get(url)
            self.add_overlay()
            self.check_auth()
        else:
            for m in self.marketplaces:
                if m.link == url:
                    url = m.domain
            self.driver.get(url)

    def quit(self):
        logger.info(user=self.user, proxy=self.proxy, description=f"Браузер для {self.phone} закрыт")
        self.driver.quit()
