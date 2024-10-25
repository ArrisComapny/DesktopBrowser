import time
import logging

from typing import Type
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from pyodbc import Error as PyodbcError
from sqlalchemy.exc import OperationalError

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
        markets = self.session.query(Market).filter_by(marketplace=marketplace, name_company=name_company).first()
        return markets

    @retry_on_exception()
    def check_user(self, login: str, password: str) -> bool:
        user = self.session.query(User).filter(func.lower(User.user) == login.lower(),
                                               User.password == password).first()
        return user is not None

    @retry_on_exception()
    def get_key(self) -> str:
        key = self.session.query(SecretKey).first()
        return key.key
