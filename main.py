import sys
from PyQt5 import QtWidgets

from log_api import logger
from apps import LoginWindow  # Главное окно авторизации

if __name__ == '__main__':
    try:
        # Инициализация Qt-приложения
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")  # Стиль интерфейса

        # Кастомизация всплывающих подсказок и кнопок справки
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

        # Запуск окна логина
        login_window = LoginWindow()
        login_window.show()

        # Запуск главного цикла приложения
        sys.exit(app.exec_())

    except Exception as e:
        # Логирование непредвиденных ошибок
        logger.error(description=str(e))
