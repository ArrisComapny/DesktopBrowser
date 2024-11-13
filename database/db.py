import time
import logging

from functools import wraps
from typing import Type, List
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from pyodbc import Error as PyodbcError
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, func as f

from config import DB_URL
from database.models import *

logger = logging.getLogger(__name__)


def retry_on_exception(retries=3, delay=10):
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
                    logger.debug(f"Error occurred: {e}. Retrying {attempt}/{retries} after {delay} seconds...")
                    time.sleep(delay)
                    if hasattr(self, 'session'):
                        self.session.rollback()
                except Exception as e:
                    logger.error(f"An unexpected error occurred: {e}. Rolling back...")
                    if hasattr(self, 'session'):
                        self.session.rollback()
                    raise e
            raise RuntimeError("Max retries exceeded. Operation failed.")
        return wrapper
    return decorator


class DbConnection:
    def __init__(self, echo: bool = False) -> None:
        self.engine = create_engine(url=DB_URL, echo=echo, pool_pre_ping=True)
        self.session = Session(self.engine)

    @retry_on_exception()
    def info(self) -> list[Type[Market]]:
        markets = self.session.query(Market).all()
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
    def check_user(self, login: str, password: str) -> bool:
        user = self.session.query(User).filter(f.lower(User.user) == login.lower(),
                                               User.password == password).first()
        return user is not None

    @retry_on_exception()
    def get_key(self) -> str:
        key = self.session.query(SecretKey).first()
        return key.key

    @retry_on_exception()
    def get_phone_message(self, user: str, phone: str, marketplace: str) -> str:
        retry = 0
        max_retry = 20
        while retry <= max_retry:
            check = self.session.query(PhoneMessage).filter(
                f.lower(PhoneMessage.user) == user.lower(),
                PhoneMessage.phone == phone,
                PhoneMessage.marketplace == marketplace
            ).order_by(PhoneMessage.time_request.asc()).first()
            if check is None:
                raise Exception('Ошибка получения сообщениия')
            else:
                if check.message is None:
                    retry += 1
                    time.sleep(5)
                else:
                    return check.message
        else:
            check = self.session.query(PhoneMessage).filter(
                f.lower(PhoneMessage.user) == user.lower(),
                PhoneMessage.phone == phone,
                PhoneMessage.marketplace == marketplace
            ).order_by(PhoneMessage.time_request.asc()).first()
            self.session.delete(check)
            self.session.commit()
            raise Exception("Превышен лимит ожидания сообщения")

    @retry_on_exception()
    def check_phone_message(self, user: str, phone: str, time_request: datetime) -> None:
        retry = 0
        max_retry = 20
        while retry <= max_retry:
            user_check = self.session.query(PhoneMessage).filter(
                f.lower(PhoneMessage.user) == user.lower(),
                PhoneMessage.phone == phone,
                PhoneMessage.time_request >= time_request - timedelta(minutes=2),
                PhoneMessage.time_response.is_(None)
            ).first()
            if user_check:
                raise Exception("Данный пользователь уже ждёт авторизации")
            check = self.session.query(PhoneMessage).filter(
                PhoneMessage.phone == phone,
                PhoneMessage.time_request >= time_request - timedelta(minutes=2),
                PhoneMessage.time_response.is_(None)
            ).first()
            if check is not None:
                retry += 1
                time.sleep(5)
            else:
                break
        else:
            raise Exception("Превышен лимит ожидания очереди")

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

