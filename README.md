## 🐍 Установка Python (Windows)

1. Скачайте Python 3.10+ с официального сайта: [python.org/downloads](https://www.python.org/downloads/windows/)
2. Во время установки обязательно отметьте **"Add Python to PATH"**
3. После установки проверьте в терминале:

```bash
python --version
```

---

## 📥 Клонирование проекта с GitHub (Windows)

Если у вас установлен Git:

```bash
git clone https://github.com/<GIT>/DesktopBrowser.git
cd DesktopBrowser
```

Если Git не установлен:

1. Перейдите на репозиторий на GitHub
2. Нажмите кнопку **"Code" → "Download ZIP"**
3. Распакуйте архив в удобное место
4. Откройте командную строку в этой папке

---

# 🧭 DesktopBrowser

**DesktopBrowser** — это десктопное приложение на Python для автоматизированного запуска браузеров через прокси и авторизации в ЛК маркетплейсов (Ozon, Wildberries, Yandex).

---

## 📁 Структура проекта

```
DesktopBrowser/
│
├── apps/
│   ├── login_app.py              # Окно логина, проверка версии, переход в браузер
│   └── browser_app.py            # Выбор компании/маркетплейса, запуск браузера
│
├── database/
│   ├── db.py                     # Работа с базой данных (SQLAlchemy)
│   └── models.py                 # ORM-модели базы
│
├── docs/
│   ├── faq.md                    # FAQ
│   ├── setup_marketplaces.md     # Настройка кабинетов маркетплейсов
│   ├── setup_postgres.md         # Установка и настройка PostgreSQL на Ubuntu
│   ├── setup_squid_proxy.md      # Установка и настройка Squid Proxy на Ubuntu
│   ├── setup_yandex_mail.md      # Создание и настройка Yandex-почты
│   └── work_database.md          # Раабота с базой
│
├── email_api/
│   └── email.py                  # Получение кода по email (Yandex.Mail)
│
├── log_api/
│   └── log.py                    # Логирование в файл и на сервер
│
├── web_driver/
│   ├── create_extension_proxy.py # Генерация Chrome-расширения для прокси
│   └── wd.py                     # WebDriver и логика авторизации (Ozon, WB, Yandex)
│
├── .gitignore                    # Исключения для git
├── config.example.py             # Пример конфигурации (копируется в config.py)
├── create_tables.py              # Скрипт создания таблиц и первоначальных записей в базе
├── main.py                       # Точка входа, запускает интерфейс
│
├── build.bat                     # Сборка через PyInstaller (Windows)
├── my.spec                       # Конфигурация сборки PyInstaller
├── requirements.txt              # Список зависимостей проекта
│
├── chrome.png                    # Иконка основного окна
├── info.png                      # Иконка справки (всплывающие подсказки)
└── README.md                     # Этот файл
```

---

## ⚙️ Установка и запуск

### 1. 📥 Установка зависимостей (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. ⚙️ Настройка `config.py`

Создайте файл:

```bash
cp config.example.py config.py
```

И отредактируйте:

```python
DB_USER = "postgres"
DB_PASS = "your_password"
DB_HOST = "your_host"
DB_NAME = "your_db"
LOG_SERVER_URL = "http://your-log-endpoint"
```
>🗄️ [Настройка PostgreSQL](docs/setup_postgres.md)

### 3. 🚀 Запуск

```bash
python main.py
```

---

## 🧠 Как работает

### 🔐 Авторизация

- `LoginWindow` проверяет логин, версию, ключ.
- Если всё ок — запускается `BrowserApp`.

### 🌍 Браузер

- Выбор маркетплейса и компании.
- Запуск `WebDriver`, автоматический вход:
  - Ozon: email и SMS
  - WB: номер телефона
  - Yandex: почта + SMS
- Ввод кода подтверждения.
- Проверка успешного входа.

### 🔄 Обновления

- Сравнение версии из БД.
- Если не совпадает — скачивается zip, обновляется код, перезапуск.

---

## 🧪 Сборка `.exe` (Windows)

Для сборки приложения в исполняемый `.exe`-файл используется [PyInstaller](https://pyinstaller.org/).

### 📌 Требования:
- Windows 10/11 x64
- Python 3.10+
- Установлен Google Chrome
- Все зависимости установлены (см. выше)

### 🔧 Подготовка:

> Убедитесь, что активировано виртуальное окружение, и выполнены шаги по установке зависимостей.

---

### 🚀 Сборка (одна команда):

```bash
pyinstaller my.spec
```

или используйте подготовленный скрипт:

```bash
build.bat
```

### 📁 Результат:

Собранное приложение появится в папке:

```
DesktopBrowser/dist/
```

Файл `ProxyBrowser.exe` можно запускать напрямую, передавать другим пользователям или упаковать в архив.

---

### 📦 Что включается в `.exe`:

- Весь проект (код, зависимости, UI, Chrome профиль)
- `chrome.png`, `info.png`

---

### 💡 Рекомендации:

- Не размещайте `.exe` на рабочем столе или в системных папках (Документы, Загрузки).
- Поместите приложение в отдельную директорию с полными правами на чтение/запись.
---

## 🗂️ Рабочие папки

- `chrome_profile/` — профили браузеров
- `proxy_auth/` — временные ZIP расширения
- `log/` — лог-файлы
- `credentials.json` — запомненные настройки

---

## 📤 Логирование

- Сохраняется в `log/YYYY-MM-DD.log`
- Отправляется на `LOG_SERVER_URL` через POST

---

## 📞 Обратная связь

Если возникли ошибки при авторизации, логины или прокси — проверьте:
- подключение к интернету
- настройки `config.py`
- наличие Chrome на ПК

## ⚠️ Требования для запуска приложения

Для корректной работы **DesktopBrowser** необходимо:

1. **PostgreSQL база данных**
   - Настроенная структура (таблицы пользователей, компаний, маркетов, ключей и логов)
   - Доступ через параметры в `config.py`

2. **Виртуальный номер телефона**
   - Для получения SMS-кодов авторизации
   - Рекомендуемый сервис: [Novofon](https://novofon.ru)

3. **API-сервер**
   - Используется для логирования действий (`LOG_SERVER_URL`)
   - Принимает POST-запросы с логами и кодами подтверждения (email/SMS)
   - Является связующим звеном между приложением, почтой и БД

4. **Прокси-сервер**
   - Поддержка авторизации (user:pass@ip:port)
   - Используется для каждого браузера/сессии

> Все эти компоненты должны быть доступны до запуска приложения.

## 📖 Дополнительные инструкции

- 🗄️ [Настройка PostgreSQL](docs/setup_postgres.md)
- 🌐 [Настройка Squid Proxy](docs/setup_squid_proxy.md)
- ☁️ [API-сервер: проект](https://github.com/ricktayler/Remote-access-api)
- 👤 [Создание аккаунтов для маркетплейсов](docs/setup_marketplaces.md)
- 📘 [Инструкция по работе с базой](docs/work_database.md)
- 📮 [Инструкция по настройке Yandex-почты](docs/setup_yandex_mail.md)
- ❓  [FAQ](docs/faq.md)
