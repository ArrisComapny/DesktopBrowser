from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from cryptography.fernet import Fernet

from config import DB_URL
from database.models import Base, SecretKey, Version, Marketplace, Group


def create_tables() -> None:
    """Создаёт таблицы в БД из моделей и добавляет базовые записи"""

    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)
    print("✅ Таблицы успешно созданы (если их не было).")

    with Session(engine) as session:
        # SecretKey
        if not session.query(SecretKey).first():
            key = Fernet.generate_key().decode()
            session.add(SecretKey(key=key))
            print("🔐 Добавлен ключ шифрования в SecretKey")

        # Version
        if not session.query(Version).first():
            session.add(Version(version="1.0.0", url=""))
            print("📦 Добавлена версия 1.0.0 в Version")

        # Marketplaces
        if not session.query(Marketplace).first():
            marketplaces = [
                Marketplace(marketplace="WB", link="https://seller-auth.wildberries.ru", domain="https://seller.wildberries.ru"),
                Marketplace(marketplace="Ozon", link="https://id.ozon.ru", domain="https://seller.ozon.ru/app/dashboard/main"),
                Marketplace(marketplace="Yandex", link="https://passport.yandex.ru", domain="https://partner.market.yandex.ru/business"),
            ]
            session.add_all(marketplaces)
            print("🛒 Добавлены записи в Marketplaces")

        # Groups
        if not session.query(Group).first():
            groups = [
                Group(group="ALL", comment="Допуск ко всем магазам"),
                Group(group="Manager OZON", comment="Менеджеры Ozon"),
                Group(group="Manager WB", comment="Менеджеры WB"),
                Group(group="Manager YANDEX", comment="Менеджеры Yandex"),
            ]
            session.add_all(groups)
            print("👥 Добавлены записи в Group")

        session.commit()


if __name__ == "__main__":
    create_tables()
