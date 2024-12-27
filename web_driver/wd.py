import os
import time

import undetected_chromedriver as uc

from typing import Type
from selenium import webdriver
from contextlib import suppress
from sqlalchemy.exc import IntegrityError
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumwire import webdriver as webdriver_wire
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchWindowException, TimeoutException, ElementNotInteractableException
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from database.models import Market
from database.db import DbConnection
from email_api import YandexMailClient
from log_api import logger, get_moscow_time
from .create_extension_proxy import create_proxy_auth_extension

TIME_AWAIT = 5


class AuthException(Exception):
    def __init__(self, message: str = ''):
        self.message = message
        super().__init__(self.message)


class WebDriver:
    def __init__(self, market: Type[Market], user: str, auto: bool, db_conn: DbConnection):

        self.user = user
        self.auto = auto
        self.db_conn = db_conn
        self.client_id = market.client_id
        self.mail = market.connect_info.mail
        self.proxy = market.connect_info.proxy
        self.phone = market.connect_info.phone
        self.token = market.connect_info.token
        self.name_company = market.name_company
        self.marketplace = market.marketplace_info
        self.pass_mail = market.connect_info.pass_mail
        self.browser_id = f"{self.phone}_{self.marketplace.marketplace.lower()}"
        self.log_startswith = f"{self.marketplace.marketplace} - {market.name_company}: "

        self.profile_path = os.path.join(os.getcwd(), f"chrome_profile/{self.browser_id}")
        os.makedirs(self.profile_path, exist_ok=True)

        # self.proxy_options = {
        #     'disable_capture': False,
        #     'proxy': {
        #         'http': f'{self.proxy}',
        #         'https': f'{self.proxy.replace("http", "https")}',
        #         'no_proxy': 'localhost,127.0.0.1'
        #     }
        # }

        self.chrome_options = uc.ChromeOptions()

        self.chrome_options.add_argument("--lang=ru")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-gpu")
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

        self.proxy_auth_path = os.path.join(os.getcwd(), f"proxy_auth")
        os.makedirs(self.proxy_auth_path, exist_ok=True)

        proxy_zip = create_proxy_auth_extension(self.proxy_auth_path, self.proxy)
        self.chrome_options.add_extension(os.path.join(self.proxy_auth_path, proxy_zip))

        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)

        # if self.marketplace.marketplace == 'Yandex':
        #     self.proxy_auth_path = os.path.join(os.getcwd(), f"proxy_auth")
        #     os.makedirs(self.proxy_auth_path, exist_ok=True)
        #
        #     proxy_zip = create_proxy_auth_extension(self.proxy_auth_path, self.proxy)
        #     self.chrome_options.add_extension(os.path.join(self.proxy_auth_path, proxy_zip))
        #     self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        # else:
        #     self.chrome_options.add_argument("--disable-extensions")
        #     self.driver = webdriver_wire.Chrome(service=self.service,
        #                                         options=self.chrome_options,
        #                                         seleniumwire_options=self.proxy_options)

        self.driver.maximize_window()

    def check_auth(self):
        try:
            self.add_overlay()
            WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete")
            last_url = None
            for _ in range(6):
                self.add_overlay()
                if last_url == self.driver.current_url:
                    break
                last_url = self.driver.current_url
                WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete")
                time.sleep(TIME_AWAIT)
            else:
                Exception("Превышено время загрузки страницы")

            if self.marketplace.link in last_url:
                self.add_overlay()
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Автоматизация запущена")
                if self.marketplace.marketplace == 'Ozon':
                    self.ozon_auth(self.marketplace)
                elif self.marketplace.marketplace == 'WB':
                    self.wb_auth(self.marketplace)
                elif self.marketplace.marketplace == 'Yandex':
                    self.ya_auth(self.marketplace)
            if self.marketplace.domain in last_url:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
            if 'https://id.yandex.ru' in last_url:
                self.driver.get(f'{self.marketplace.domain}/{self.client_id}/marketplace')
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
            self.remove_overlay()
        except NoSuchWindowException:
            self.quit('Окно браузера было преждевременно закрыто')
        except Exception as e:
            self.quit(str(e).splitlines()[0])

    def wb_auth(self, marketplace):
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод номера {self.phone}")

        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                input_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='phone-input']")))
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

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Проверка заявки на СМС на номер {self.phone}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user, phone=self.phone, time_request=time_request)
        self.remove_overlay()
        button_phone.click()
        self.add_overlay()

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

        with suppress(TimeoutException):
            timer_element = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'FormPhoneInputBorderless__error-fWDiaZx8UW')]//span")))
            raise Exception(timer_element.text)

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Ожидание кода на номер {self.phone}")

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.phone,
                                             marketplace=marketplace.marketplace)

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Код на номер {self.phone} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод кода {mes}")

        try:
            time.sleep(TIME_AWAIT)
            inputs_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.presence_of_all_elements_located((By.CSS_SELECTOR,
                                                                      "[data-testid='sms-code-input']")))

            if len(mes) == len(inputs_code):
                self.remove_overlay()
                for i, input_code in enumerate(inputs_code):
                    input_code.send_keys(mes[i])
                self.add_overlay()
            else:
                raise Exception('Ошибка ввода кода')
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Вход в ЛК")
        for _ in range(4):
            time.sleep(TIME_AWAIT)
            if marketplace.domain in self.driver.current_url:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
                return
        else:
            logger.info(user=self.user, proxy=self.proxy,
                        description=f"{self.log_startswith}Автоматизация завершена, вход не подтверждён")

    def ozon_auth(self, marketplace):
        with suppress(TimeoutException):
            h2 = WebDriverWait(self.driver, TIME_AWAIT).until(expected_conditions.presence_of_element_located((
                By.XPATH, "//h2[@qa-id='ozonIdCredentialSettingsTitle']")))
            if h2:
                self.driver.get(marketplace.domain)
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
                return

        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод почты {self.mail}")
        for _ in range(3):
            try:
                time.sleep(TIME_AWAIT)
                button_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.presence_of_all_elements_located((By.CSS_SELECTOR, '.content button')))[-2]
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
                    expected_conditions.presence_of_all_elements_located((By.CSS_SELECTOR, '.content button')))[-3]
                break
            except (TimeoutException, IndexError):
                self.driver.refresh()
                self.add_overlay()
        else:
            raise Exception('Страница не получена')

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Проверка заявки на Email {self.mail}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)
        self.remove_overlay()
        button_push.click()
        self.add_overlay()

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Ожидание кода на Email {self.mail}")

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

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Код на Email {self.mail} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод кода {mes}")

        try:
            time.sleep(TIME_AWAIT)
            input_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "input[type='number']")))

            self.remove_overlay()
            input_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Вход в ЛК")

        time.sleep(TIME_AWAIT)
        with suppress(TimeoutException):
            WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.presence_of_element_located((By.CLASS_NAME,
                                                                 'csma-ozon-id-page')))
            self.add_overlay()
            self.driver.get(marketplace.domain)
            time.sleep(TIME_AWAIT)
            if marketplace.domain in self.driver.current_url:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
            else:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Автоматизация завершена, вход не подтверждён")
            return

        try:
            button_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.presence_of_all_elements_located((By.CSS_SELECTOR, '.content button')))[-2]
        except (TimeoutException, IndexError) as e:
            raise Exception(f'Нет кнопки подтверждения телефона. {e}')

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Проверка заявки на СМС на номер {self.phone}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.phone,
                                         time_request=time_request)
        try:
            self.remove_overlay()
            button_phone.click()
            self.add_overlay()
        except ElementNotInteractableException as e:
            raise Exception(f'Нет кнопки подтверждения телефона. {e}')

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Ожидание кода на номер {self.phone}")

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

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Код на номер {self.phone} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод кода {mes}")

        try:
            time.sleep(TIME_AWAIT)
            input_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "input[type='number']")))

            self.remove_overlay()
            input_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Вход в ЛК")
        for _ in range(4):
            self.add_overlay()
            time.sleep(TIME_AWAIT)
            self.driver.get(marketplace.domain)
            if marketplace.domain in self.driver.current_url:
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
                return
        else:
            logger.info(user=self.user, proxy=self.proxy,
                        description=f"{self.log_startswith}Автоматизация завершена, вход не подтверждён")

    def ya_auth(self, marketplace):
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод почты {self.mail}")

        for _ in range(3):
            try:
                with suppress(TimeoutException):
                    time.sleep(TIME_AWAIT)
                    input_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                        expected_conditions.element_to_be_clickable((By.ID, 'passp-field-login')))
                    input_mail.send_keys(self.mail)

                    time.sleep(TIME_AWAIT)
                    button_enter_mail = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                        expected_conditions.element_to_be_clickable((By.ID, "passp:sign-in")))
                    self.remove_overlay()
                    button_enter_mail.click()
                    self.add_overlay()

                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Ввод пароля от {self.mail}")
                time.sleep(TIME_AWAIT)
                input_pass = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.ID, 'passp-field-passwd')))
                input_pass.send_keys(self.pass_mail)

                time.sleep(TIME_AWAIT)
                button_enter_pass = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.ID, "passp:sign-in")))
                self.remove_overlay()
                button_enter_pass.click()
                self.add_overlay()

                time.sleep(TIME_AWAIT)
                button_enter = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                    expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "button[data-t='button:action']")))
                break
            except TimeoutException:
                self.driver.refresh()
                self.add_overlay()
        else:
            raise Exception('Страница не получена')

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Проверка заявки на СМС на номер {self.phone}")

        time_request = get_moscow_time()
        self.db_conn.check_phone_message(user=self.user, phone=self.phone, time_request=time_request)
        self.remove_overlay()
        button_enter.click()
        self.add_overlay()

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Ожидание кода на номер {self.phone}")

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

        logger.info(user=self.user, proxy=self.proxy,
                    description=f"{self.log_startswith}Код на номер {self.phone} получен: {mes}")
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Ввод кода {mes}")

        try:
            time.sleep(TIME_AWAIT)
            inputs_code = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
                expected_conditions.element_to_be_clickable((By.ID, 'passp-field-phoneCode')))
            self.remove_overlay()
            inputs_code.send_keys(mes)
            self.add_overlay()
        except TimeoutException:
            raise Exception('Отсутствует поле ввода кода')

        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Вход в ЛК")
        for _ in range(4):
            self.add_overlay()
            time.sleep(TIME_AWAIT)
            if 'https://id.yandex.ru' in self.driver.current_url:
                self.driver.get(f'{self.marketplace.domain}/{self.client_id}/marketplace')
                logger.info(user=self.user, proxy=self.proxy,
                            description=f"{self.log_startswith}Вход в ЛК выполнен")
                return
        else:
            logger.info(user=self.user, proxy=self.proxy,
                        description=f"{self.log_startswith}Автоматизация завершена, вход не подтверждён")

    def add_overlay(self):
        self.driver.execute_script(f"""
            if (!document.getElementById('block-overlay')) {{
                let overlay = document.createElement('div');
                overlay.id = 'block-overlay';
                Object.assign(overlay.style, {{
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
                }});
                overlay.innerText = 'Идёт авторизация, пожалуйста, подождите. Кабинет {self.name_company}.';
                document.body.appendChild(overlay);
            }}
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
        logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Браузер открыт")
        if self.auto:
            logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Авторизация")
            self.driver.get(url)
            self.add_overlay()
            self.check_auth()
        else:
            if self.marketplace.marketplace == 'Yandex':
                self.driver.get(f'{self.marketplace.domain}/{self.client_id}/marketplace')
            else:
                self.driver.get(self.marketplace.domain)

    def quit(self, text: str = None):
        if text:
            logger.error(user=self.user, proxy=self.proxy,
                         description=f"{self.log_startswith}Ошибка автоматизации: {text}")
            self.driver.quit()
            raise AuthException(f"{text}\n\nПопробуйте позднее")
        else:
            logger.info(user=self.user, proxy=self.proxy, description=f"{self.log_startswith}Браузер закрыт")
            self.driver.quit()
