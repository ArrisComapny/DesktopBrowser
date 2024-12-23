import time

from functools import wraps
from typing import Type, List
from sqlalchemy.orm import Session
from pyodbc import Error as PyodbcError
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, func as f, and_

from config import DB_URL
from log_api import logger
from database.models import *


def retry_on_exception(retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    result = func(self, *args, **kwargs)
                    return result
                except (OperationalError, PyodbcError) as e:
                    attempt += 1
                    logger.debug(f"База данных. Произошла ошибка: {e}. Повторная попытка {attempt}/{retries}")
                    time.sleep(delay)
                    if hasattr(self, 'session'):
                        self.session.rollback()
                except Exception as e:
                    logger.error(f"База данных. Произошла непредвиденая ошибка: {e}.")
                    if hasattr(self, 'session'):
                        self.session.rollback()
                    raise e
            raise RuntimeError("База данных. Попытки подключения исчерпаны")

        return wrapper

    return decorator


class DbConnection:
    def __init__(self, echo: bool = False) -> None:
        self.engine = create_engine(url=DB_URL,
                                    echo=echo,
                                    pool_size=10,
                                    max_overflow=5,
                                    pool_timeout=30,
                                    pool_recycle=1800,
                                    pool_pre_ping=True,
                                    connect_args={"keepalives": 1,
                                                  "keepalives_idle": 180,
                                                  "keepalives_interval": 60,
                                                  "keepalives_count": 20,
                                                  "connect_timeout": 10})
        self.session = Session(self.engine)

    @retry_on_exception()
    def info(self, group: str) -> list[Type[Market]]:
        if group.lower().strip() == 'all':
            markets = self.session.query(Market).all()
        elif group.lower().strip() == 'manager ozon':
            markets = self.session.query(Market).filter_by(marketplace='Ozon').all()
        elif group.lower().strip() == 'manager wb':
            markets = self.session.query(Market).filter_by(marketplace='WB').all()
        elif group.lower().strip() == 'manager yandex':
            markets = self.session.query(Market).filter_by(marketplace='Yandex').all()
        else:
            markets = (self.session.query(Market).join(GroupMarket, and_(
                Market.marketplace == GroupMarket.marketplace,
                Market.name_company == GroupMarket.name_company
            )).filter(GroupMarket.group == group)).all()
        return markets

    @retry_on_exception()
    def get_market(self, marketplace: str, name_company: str) -> Type[Market]:
        market = self.session.query(Market).filter_by(marketplace=marketplace, name_company=name_company).first()
        return market

    @retry_on_exception()
    def get_marketplaces(self) -> List[Type[Marketplace]]:
        marketplaces = self.session.query(Marketplace).all()
        return marketplaces

    @retry_on_exception()
    def check_user(self, login: str, password: str):
        user = self.session.query(User).filter(f.lower(User.user) == login.lower(),
                                               User.password == password).first()
        if user is not None:
            return user.group

    @retry_on_exception()
    def get_key(self) -> str:
        key = self.session.query(SecretKey).first()
        return key.key

    @retry_on_exception()
    def get_version(self) -> Type[Version]:
        version = self.session.query(Version).first()
        return version

    @retry_on_exception()
    def get_phone_message(self, user: str, phone: str, marketplace: str) -> str:
        check = None
        for _ in range(20):
            check = self.session.query(PhoneMessage).filter(
                f.lower(PhoneMessage.user) == user.lower(),
                PhoneMessage.phone == phone,
                PhoneMessage.marketplace == marketplace
            ).order_by(PhoneMessage.time_request.desc()).first()

            if check is None:
                raise Exception('Ошибка получения сообщения')

            if check.message is not None:
                return check.message

            self.session.expire(check)
            time.sleep(5)

        self.session.delete(check)
        self.session.commit()
        raise Exception("Превышен лимит ожидания сообщения")

    @retry_on_exception()
    def check_phone_message(self, user: str, phone: str, time_request: datetime) -> None:
        for _ in range(20):
            check = self.session.query(PhoneMessage).filter(
                PhoneMessage.phone == phone,
                PhoneMessage.time_request >= time_request - timedelta(minutes=2),
                PhoneMessage.time_response.is_(None)
            ).all()
            if any([row.user.lower() == user.lower() for row in check]):
                raise Exception("Предыдущая аторизация не завершена.")

            if not check:
                break
            self.session.expire(check)
            time.sleep(5)
        else:
            raise Exception("Превышен лимит ожидания очереди на авторизацию")

    @retry_on_exception()
    def add_phone_message(self, user: str, phone: str, marketplace: str, time_request: datetime) -> None:
        user = self.session.query(User).filter(f.lower(User.user) == user.lower()).first()
        if user is None:
            raise Exception("Такого пользователя не существует")
        new = PhoneMessage(user=user.user,
                           phone=phone,
                           marketplace=marketplace,
                           time_request=time_request)
        self.session.add(new)
        self.session.commit()

    @retry_on_exception()
    def update_phone_message(self, user: str, phone: str, marketplace: str, message: str,
                             time_response: datetime) -> None:
        mes = self.session.query(PhoneMessage).filter(
            f.lower(PhoneMessage.user) == user.lower(),
            PhoneMessage.phone == phone,
            PhoneMessage.marketplace == marketplace,
            PhoneMessage.time_response.is_(None),
            PhoneMessage.message.is_(None),
            PhoneMessage.time_request <= time_response + timedelta(seconds=2),
            PhoneMessage.time_request >= time_response - timedelta(minutes=2)
        ).order_by(PhoneMessage.time_request.asc()).first()

        if mes:
            mes.time_response = time_response
            mes.message = message
            self.session.commit()
        else:
            raise Exception("Нет запроса")
