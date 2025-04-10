from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, DateTime, Text, String, Integer
from sqlalchemy import UniqueConstraint, MetaData, ForeignKeyConstraint, Identity, ForeignKey


metadata = MetaData()
Base = declarative_base(metadata=metadata)


class Market(Base):
    """
    Таблица markets — содержит информацию о компаниях, привязанных к маркетплейсам.

    Поля:
    - marketplace: название маркетплейса (WB, Ozon, Yandex)
    - name_company: название компании
    - phone: номер телефона РФ без кода страны, используемый для входа
    - entrepreneur: ФИО владельца или ИП
    - client_id: идентификатор клиента на платформе

    Связи:
    - marketplace_info: отношение к Marketplace
    - connect_info: отношение к Connect

    Ограничения:
    - уникальность по паре marketplace + name_company + phone
    - уникальность по паре marketplace + name_company
    """
    __tablename__ = 'markets'

    id = Column(Integer, Identity(), primary_key=True)
    marketplace = Column(String(length=255),
                         ForeignKey('marketplaces.marketplace', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    name_company = Column(String(length=255), nullable=False)
    phone = Column(String(length=255), ForeignKey('connects.phone', ondelete='CASCADE', onupdate='CASCADE'),
                   nullable=False)
    entrepreneur = Column(String(length=255), nullable=True)
    client_id = Column(String(length=255), nullable=True)

    marketplace_info = relationship("Marketplace", back_populates="markets")
    connect_info = relationship("Connect", back_populates="markets")

    __table_args__ = (
        UniqueConstraint('marketplace', 'name_company', 'phone', name='markets_unique'),
        UniqueConstraint('marketplace', 'name_company', name='market_unique'),
    )


class Marketplace(Base):
    """
    Таблица marketplaces — список доступных платформ.

    Поля:
    - marketplace: название маркетплейса (WB, Ozon, Yandex)
    - link: ссылка на сайт
    - domain: домен для определения успешной авторизации

    Связи:
    - markets: список связанных компаний (Market)
    """
    __tablename__ = 'marketplaces'

    marketplace = Column(String(length=255), primary_key=True, nullable=False)
    link = Column(String(length=1000), nullable=False)
    domain = Column(String(length=255), nullable=False)

    markets = relationship("Market", back_populates="marketplace_info")


class Connect(Base):
    """
    Таблица connects — настройки подключения и авторизации для каждой компании.

    Поля:
    - phone: номер телефона РФ без кода страны, используемый для входа
    - proxy: прокси-сервер http://<login>:<assword>@<host>:<port>
    - mail: Yandex-почта для получения кодов на Ozon и для подключенния к Yandex market <email>@yandex.ru
    - token: token доступа к почте Yandex, для получения кодов на Ozon
    - pass_mail: пароль к Яндекс аккаунту, для авторизации на Yandex

    Связи:
    - markets: компании, использующие это подключение

    Ограничения:
    - уникальность по паре phone + proxy
    """
    __tablename__ = 'connects'

    phone = Column(String(length=255), primary_key=True, nullable=False)
    proxy = Column(String(length=255), nullable=False)
    mail = Column(String(length=255), nullable=False)
    token = Column(String(length=255), nullable=False)
    pass_mail = Column(String(length=255), nullable=True)

    markets = relationship("Market", back_populates="connect_info")

    __table_args__ = (
        UniqueConstraint('phone', 'proxy', name='connects_unique'),
    )


class User(Base):
    """
    Таблица users — список пользователей системы.

    Поля:
    - user: логин
    - password: пароль
    - name: имя пользователя (опционально)
    - group: принадлежность к группе (определяет доступные компании)
    """
    __tablename__ = 'users'

    user = Column(String(length=255), primary_key=True, nullable=False)
    password = Column(String(length=255), nullable=False)
    name = Column(String(length=255), default=None, nullable=True)
    group = Column(String(length=255), ForeignKey('group_table.group', ondelete='CASCADE', onupdate='CASCADE'),
                   nullable=False)


class SecretKey(Base):
    """
    Таблица secret_key — хранит ключ шифрования для логинов и паролей.
    """
    __tablename__ = 'secret_key'

    key = Column(String(length=255), primary_key=True, nullable=False)


class Version(Base):
    """
    Таблица version — хранит актуальную версию и ссылку на обновление.

    Поля:
    - version: версия приложения. Пример: 1.0.4
    - url: ссылка на ZIP-обновление http://<host>:<port>/download_app
    """
    __tablename__ = 'version'

    version = Column(String(length=255), primary_key=True, nullable=False)
    url = Column(String(length=1000), primary_key=True, nullable=False)


class PhoneMessage(Base):
    """
    Таблица phone_message — отслеживание запросов авторизации по телефону или email.

    Поля:
    - user: пользователь, инициировавший авторизацию
    - phone: номер телефона
    - marketplace: маркетплейс
    - time_request: время запроса кода
    - time_response: время получения ответа
    - message: сам код (если получен)

    Используется для синхронизации кода подтверждения с автоматизацией входа.
    """
    __tablename__ = 'phone_message'

    id = Column(Integer, Identity(), primary_key=True)
    user = Column(String(length=255), ForeignKey('users.user', ondelete='SET NULL', onupdate='CASCADE'),
                  nullable=False)
    phone = Column(String(length=255), ForeignKey('connects.phone', ondelete='CASCADE', onupdate='CASCADE'),
                   nullable=False)
    marketplace = Column(String(length=255),
                         ForeignKey('marketplaces.marketplace', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    time_request = Column(DateTime, nullable=False)
    time_response = Column(DateTime, default=None, nullable=True)
    message = Column(String(length=255), default=None, nullable=True)


class Group(Base):
    """
    Таблица group_table — определяет группы пользователей и их назначения.

    Поля:
    - group: группа пользователей
    - comment: пояснение

    Используется для ограничения доступа к рынкам.
    """
    __tablename__ = 'group_table'

    group = Column(String(length=255), primary_key=True)
    comment = Column(Text, nullable=True)


class GroupMarket(Base):
    """
    Таблица group_market — связь между группами и доступными компаниями.

    Поля:
    - group: группа пользователей
    - marketplace: платформа
    - name_company: компания на платформе

    Внешний ключи:
    - (marketplace, name_company) → Market

    Используется для настройки доступа пользователей к Market.
    """
    __tablename__ = 'group_market'

    group = Column(String(length=255), ForeignKey('group_table.group', ondelete='CASCADE', onupdate='CASCADE'),
                   primary_key=True)
    marketplace = Column(String(length=255), nullable=False, primary_key=True)
    name_company = Column(String(length=255), nullable=False, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['marketplace', 'name_company'],
            ['markets.marketplace', 'markets.name_company'],
            onupdate="CASCADE"
        ),
    )


class Log(Base):
    """
    Таблица log — журнал действий пользователей и системы.

    Поля:
    - id: уникальный идентификатор лога
    - timestamp: серверное время события
    - timestamp_user: локальное время пользователя (если передано)
    - action: тип действия (INFO, ERROR, WARNING и т.д.)
    - user: логин пользователя, инициировавшего действие
    - ip_address: IP-адрес клиента
    - city: определённый по IP город
    - country: определённая по IP страна
    - proxy: использованный прокси (если есть)
    - description: текстовое описание события или ошибки
    """
    __tablename__ = 'log'

    id = Column(Integer, Identity(), primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    timestamp_user = Column(DateTime, default=None, nullable=True)
    action = Column(String(length=255), nullable=False)
    user = Column(String(length=255), ForeignKey('users.user', ondelete='SET NULL', onupdate='CASCADE'),
                  default=None, nullable=True)
    ip_address = Column(String(length=255), nullable=False)
    city = Column(String(length=255), nullable=False)
    country = Column(String(length=255), nullable=False)
    proxy = Column(String(length=255), nullable=True)
    description = Column(Text, nullable=False)
