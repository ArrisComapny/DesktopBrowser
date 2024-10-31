import logging
import requests
import socket
from datetime import datetime, timezone, timedelta

from config import LOG_SERVER_URL


class MoscowFormatter(logging.Formatter):
    def formatTime(self, record, date_fmt=None):
        moscow_time = datetime.fromtimestamp(record.created, timezone(timedelta(hours=3)))
        if date_fmt:
            return moscow_time.strftime(date_fmt)
        else:
            return moscow_time.isoformat()


class RemoteLogger:
    def __init__(self):
        self.server_url = LOG_SERVER_URL

        self.logger = logging.getLogger("RemoteLogger")
        self.logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = MoscowFormatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def log_action(self, action, user, ip_address=None):
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user": user,
            "ip_address": ip_address or self.get_ip_address(),
        }

        try:
            response = requests.post(self.server_url, json=log_data)
            response.raise_for_status()
            self.logger.info(f"Лог отправлен на сервер: {log_data}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка отправки лога на сервер: {e}")

    def get_info(self):
        try:
            response = requests.get('https://ipinfo.io/json')
            response.raise_for_status()
            data = response.json()
            ip_address = data.get('ip', 'Unknown')
            city = data.get('city', 'Unknown')
            country = data.get('country', 'Unknown')
            return {
                'ip': ip_address,
                'city': city,
                'country': country
            }
        except requests.RequestException as e:
            self.logger.error(f"Ошибка получения информации о местоположении: {e}")
            return {
                'ip': 'Unknown',
                'city': 'Unknown',
                'country': 'Unknown'
            }


sd = RemoteLogger()
print(sd.get_info())
