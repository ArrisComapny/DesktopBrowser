import os
import sys

DB_USER = "postgres"
DB_PASS = "your_password"
DB_HOST = "your_host"
DB_NAME = "your_database"
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

VERSION = "1.0.3"

NAME = 'ProxyBrowser ' + VERSION

LOG_SERVER_URL = "your_api_server_log"

if hasattr(sys, '_MEIPASS'):
    ICON_PATH = os.path.join(sys._MEIPASS, 'chrome.png')
    INFO_ICON_PATH = os.path.join(sys._MEIPASS, 'info.png')
else:
    ICON_PATH = os.path.join(os.getcwd(), 'chrome.png')
    INFO_ICON_PATH = os.path.join(os.getcwd(), 'info.png')