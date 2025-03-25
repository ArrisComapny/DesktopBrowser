# 🌐 Настройка Squid Proxy на Ubuntu 22.04 (на каждый IP — один пользователь)

Инструкция по установке и настройке прокси-сервера Squid с авторизацией и привязкой IP-адресов к пользователям.

> ℹ️ Внимание: угловые скобки (`< >`) в примерах обозначают **пользовательские данные**, которые нужно заменить на свои значения.
> Например, `<LOGIN>` → `MyLogin`, `<IP>` → `23.13.23.121`

---

## 📦 Установка Squid

```bash
sudo apt update
sudo apt install squid apache2-utils -y
```

---

## 🔐 Создание пользователей и паролей

Создайте файл, в котором будут храниться логины и пароли:

```bash
sudo touch /etc/squid/passwords
```

Для каждого пользователя (прокси-профиля) создайте логин и задайте пароль:

```bash
sudo htpasswd /etc/squid/passwords <LOGIN>
```


> 🔐 После выполнения команды система попросит вас ввести и подтвердить пароль для пользователя `<LOGIN>`.
> Пароль будет сохранён в зашифрованном виде.

Повторите команду для каждого пользователя, которому нужен доступ к прокси.

---

## ⚙️ Конфигурация Squid

Откройте файл конфигурации:

```bash
sudo nano /etc/squid/squid.conf
```

Замените его содержимое на следующее:

```conf
# Отключение проброса заголовков
forwarded_for off
via off
request_header_access X-Forwarded-For deny all
request_header_access Via deny all
request_header_access Cache-Control deny all

# Порты прокси (IP:PORT для каждого пользователя)
http_port <IP>:<PORT>

# Настройки базовой HTTP-аутентификации
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwords
auth_param basic children 5
auth_param basic realm "Proxy Authentication Required"
auth_param basic credentialsttl 1 day
auth_param basic casesensitive on

# ACL — доступ для авторизованных пользователей
acl authenticated_users proxy_auth REQUIRED

# ACL по логинам
acl <LOGIN> proxy_auth <LOGIN>

# Привязка исходящих IP к каждому логину
tcp_outgoing_address <IP> <LOGIN>

# Разрешаем доступ авторизованным
http_access allow authenticated_users

# Запрещаем всем остальным
http_access deny all
```

> `IP` — это IP на вашем сервере (если их несколько, настройте для каждого используемого IP)  
> `PORT` — произвольный порт, на котором будет работать прокси  
> `LOGIN` — должен соответствовать одному из созданных пользователей

---

## 🚀 Перезапуск Squid

```bash
sudo systemctl restart squid
```

Проверить статус:

```bash
sudo systemctl status squid
```

---

## 🔁 Проверка

Прокси доступен по:

```
http://<login>:<password>@<ip>:<port>
```

Проверить можно командой:

```
curl -x http://<login>:<password>@<ip>:<port> https://api.ipify.org
```

---

## 🛠️ Примечания

- Для каждого IP должен быть отдельный пользователь.
- IP-адреса должны быть привязаны к сетевому интерфейсу сервера (например, через `ip a`).
- Убедитесь, что порт открыт в `ufw` или `iptables`, если используется утилита.

---

## ✅ Готово!

Теперь сервер Ubuntu с Squid Proxy готов для использования с DesktopBrowser или другим приложением.