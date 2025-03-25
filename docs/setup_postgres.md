# 🗄️ Настройка PostgreSQL сервера на Ubuntu 22.04

Инструкция по установке и настройке PostgreSQL на сервере Ubuntu 22 для работы с приложением DesktopBrowser.

> ℹ️ Внимание: угловые скобки (`< >`) в примерах обозначают **пользовательские данные**, которые нужно заменить на свои значения.
> Например, `<USER>` → `admin`, `<IP>` → `176.113.82.161`

---

## 📦 Установка PostgreSQL

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Проверьте статус сервера:

```bash
sudo systemctl status postgresql
```

---

## 🛠️ Создание пользователя и базы данных

1. Перейдите в пользователя postgres:

```bash
sudo -i -u postgres
```

2. Откройте psql и создайте базу и пользователя:

```bash
psql
CREATE DATABASE <DB>;
CREATE USER <USER> WITH PASSWORD '<PASS>';
GRANT ALL PRIVILEGES ON DATABASE <DB> TO <USER>;
\q
```

3. Вернитесь к обычному пользователю:

```bash
exit
```

---

## 🔓 Настройка удалённого доступа

### 1. Измените `postgresql.conf`

Откройте файл:

```bash
sudo nano /etc/postgresql/<VERSION>/main/postgresql.conf
```

Найдите строку:

```
#listen_addresses = 'localhost'
```

Измените на:

```
listen_addresses = '*'
```

### 2. Измените `pg_hba.conf`

```bash
sudo nano /etc/postgresql/<VERSION>/main/pg_hba.conf
```

Добавьте в конец:

```
host    all             all             0.0.0.0/0               md5
```

---

## 🔄 Перезапуск PostgreSQL

```bash
sudo systemctl restart postgresql
```

---

## 🌐 Открытие порта 5432 (необязательно, только если используется UFW)

```bash
sudo ufw allow 5432/tcp
sudo ufw reload
```

---

## 🧪 Проверка подключения с клиента

```bash
psql -h <IP> -U <USER> -d <DB>
```

---

## ⚙️ Настройка в `config.py`

Укажите параметры подключения к вашей базе данных в файле `config.py` в проекте:

```python
DB_USER = "<USER>"
DB_PASS = "<PASS>"
DB_HOST = "<IP>:5432"
DB_NAME = "<DB>"
```

---

## 🧱 Создание таблиц

Выполните `create_tables.py` в проекте для создания таблиц и начальной инициализации данных:

```bash
python create_tables.py
```

---

## ✅ Готово!

Теперь сервер Ubuntu с PostgreSQL готов для работы с DesktopBrowser.