import sys

from PyQt5 import QtWidgets

from log_api import logger
from apps import LoginWindow


if __name__ == '__main__':
    try:
        app = QtWidgets.QApplication(sys.argv)
        login_window = LoginWindow()
        login_window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(description=str(e))
