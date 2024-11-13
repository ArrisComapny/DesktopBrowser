import os
import time
import undetected_chromedriver as uc

from datetime import datetime, timedelta, timezone

from seleniumwire import webdriver
from sqlalchemy.exc import IntegrityError
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchWindowException

from database.db import DbConnection

TIME_AWAIT = 5


class WebDriver:
    def __init__(self, phone: str, proxy: str, user: str):

        self.browser_id = phone
        self.user = user
        self.db_conn = DbConnection()
        self.marketplaces = self.db_conn.get_marketplaces()

        self.profile_path = os.path.join(os.getcwd(), f"chrome_profile/chrome_profile_{phone}")
        os.makedirs(self.profile_path, exist_ok=True)

        self.proxy_options = {
            'proxy': {
                'http': f'{proxy}',
                'https': f'{proxy.replace("http", "https")}',
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
        self.driver.request_interceptor = self.request_interceptor
        # self.monitor_url()
        self.driver.maximize_window()

    def request_interceptor(self, request):
        pass

    def check_auth(self):
        try:
            self.add_overlay()

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

            for m in self.marketplaces:
                if m.link in last_url:
                    if m.marketplace == 'Ozon':
                        self.ozon_auth(m.marketplace)
                    elif m.marketplace == 'WB':
                        self.wb_auth(m.marketplace)
                    break

            self.remove_overlay()
        except Exception as e:
            print(e)
            self.quit()

    def wb_auth(self, marketplace):
        time.sleep(TIME_AWAIT)
        input_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
            expected_conditions.element_to_be_clickable((By.CSS_SELECTOR,
                                                         '.SimpleInput-JIIQvb037j')))
        input_phone.send_keys(self.browser_id)
        time.sleep(TIME_AWAIT)
        button_phone = WebDriverWait(self.driver, TIME_AWAIT * 4).until(
            expected_conditions.element_to_be_clickable((By.XPATH,
                                                         '//*[@data-testid="submit-phone-button"]')))

        time_request = datetime.now(tz=timezone(timedelta(hours=3)))
        self.db_conn.check_phone_message(user=self.user,
                                         phone=self.browser_id,
                                         time_request=time_request)
        self.remove_overlay()
        button_phone.click()
        self.add_overlay()

        rate = 0
        max_rate = 3
        while rate <= max_rate:
            try:
                time_request = datetime.now(tz=timezone(timedelta(hours=3)))
                self.db_conn.add_phone_message(user=self.user,
                                               phone=self.browser_id,
                                               marketplace=marketplace,
                                               time_request=time_request)
                break
            except IntegrityError:
                rate += 1
                time.sleep(5)
        else:
            raise Exception('Ошибка параллельных запросов')

        mes = self.db_conn.get_phone_message(user=self.user,
                                             phone=self.browser_id,
                                             marketplace=marketplace)
        print(mes)

    def ozon_auth(self, marketplace):
        pass

    def add_overlay(self):
        self.driver.execute_script("""
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
        """)

    def remove_overlay(self):
        self.driver.execute_script("""
            let overlay = document.getElementById('block-overlay');
            if (overlay) overlay.remove();
        """)

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
                self.check_auth()
            else:
                self.load_url(url)
        except NoSuchWindowException:
            self.load_url(url)

    def load_url(self, url: str):
        self.driver.get(url)
        self.check_auth()

    def quit(self):
        self.driver.quit()
