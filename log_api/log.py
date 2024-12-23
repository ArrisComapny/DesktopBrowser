import os
import logging
import requests
import warnings

from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from urllib3.exceptions import InsecureRequestWarning

from config import LOG_SERVER_URL

warnings.simplefilter("ignore", InsecureRequestWarning)


def get_moscow_time(timeout: int = 60, log_api: bool = False):
    try:
        response = requests.get("https://timeapi.io/api/Time/current/zone?timeZone=Europe/Moscow",
                                timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()
        moscow_time = datetime.fromisoformat(data['dateTime'].split('.')[0])
        return moscow_time
    except Exception as e:
        if not log_api:
            with suppress(Exception):
                logger.error(description=f"Ошибка при получении времени: {e}")
        return datetime.now(tz=timezone(timedelta(hours=3)))


class MoscowFormatter(logging.Formatter):
    def formatTime(self, record, date_fmt=None):
        moscow_time = get_moscow_time(timeout=5, log_api=True)
        if date_fmt:
            return moscow_time.strftime(date_fmt)
        else:
            return moscow_time.isoformat()


class RemoteLogger:
    def __init__(self):
        self.server_url = LOG_SERVER_URL
        self.executor = ThreadPoolExecutor(max_workers=10)

        log_dir = "log"
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"{get_moscow_time(timeout=5, log_api=True).strftime('%Y-%m-%d')}.log")

        self.logger = logging.getLogger("RemoteLogger")
        self.logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        formatter = MoscowFormatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def error(self, user: str = None, description: str = '', proxy: str = None) -> None:
        self.logger.error(f"{description}")
        self.log_action('ERROR', user=user, description=description, proxy=proxy)

    def waring(self, user: str = None, description: str = '', proxy: str = None):
        self.log_action('WARRING', user=user, description=description, proxy=proxy)

    def info(self, user: str = None, description: str = None, proxy: str = None) -> None:
        self.logger.info(f"{description}")
        self.log_action('INFO', user=user, description=description, proxy=proxy)

    def log_action(self, action: str, user: str, description: str = '', proxy: str = None) -> None:
        self.executor.submit(self._send_log, action, user, description, proxy)

    def _send_log(self, action: str, user: str, description: str = '', proxy: str = None) -> None:
        info = self.get_info()

        log_data = {
            "timestamp": get_moscow_time(timeout=5, log_api=True).isoformat(),
            "timestamp_user": datetime.now().isoformat(),
            "action": action,
            "user": user,
            "ip_address": info.get('ip') or 'Unknown',
            "city":  info.get('city') or 'Unknown',
            "country": info.get('country') or 'Unknown',
            "proxy": proxy,
            "description": description
        }

        try:
            response = requests.post(self.server_url, json=log_data, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка отправки лога на сервер: {e}")
        except Exception as e:
            self.logger.error(f"log_action: {e}")

    def get_info(self) -> dict:
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5, verify=False)
            response.raise_for_status()
            data = response.json()
            return {
                'ip': data.get('ip'),
                'city': data.get('city'),
                'country': data.get('country')
            }
        except requests.RequestException as e:
            self.logger.error(f"get_info: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"get_info: {e}")


logger = RemoteLogger()
