import sys

from PyQt5 import QtWidgets

from log_api import logger
from apps import LoginWindow


if __name__ == '__main__':
    try:
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setStyleSheet("""
            QToolButton { 
                border: none; 
                padding: 0; 
                }
            QToolTip {
                max-width: 200px;
                background-color: #fffbeb;
                padding: 10px 5px;
                font-size: 10pt;
                }
        """)
        login_window = LoginWindow()
        login_window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(description=str(e))
