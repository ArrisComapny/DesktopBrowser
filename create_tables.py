from database.models import Base
from sqlalchemy import create_engine

from config import DB_URL


def create_tables() -> None:
    """Создаёт таблицы в БД из моделей"""
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)
    print("✅ Таблицы успешно созданы (если их не было).")


if __name__ == "__main__":
    create_tables()
