from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, MetaData, Integer, Identity, ForeignKey, UniqueConstraint, DateTime, Text, \
    ForeignKeyConstraint

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class Market(Base):
    """Модель таблицы clients."""
    __tablename__ = 'markets'

    id = Column(Integer, Identity(), primary_key=True)
    marketplace = Column(String(length=255), ForeignKey('marketplaces.marketplace', onupdate="CASCADE"), nullable=False)
    name_company = Column(String(length=255), nullable=False)
    phone = Column(String(length=255), ForeignKey('connects.phone', onupdate="CASCADE"), nullable=False)
    entrepreneur = Column(String(length=255), nullable=False)
    client_id = Column(String(length=255), nullable=False)

    marketplace_info = relationship("Marketplace", back_populates="markets")
    connect_info = relationship("Connect", back_populates="markets")

    __table_args__ = (
        UniqueConstraint('marketplace', 'name_company', 'phone', name='markets_unique'),
        UniqueConstraint('marketplace', 'name_company', name='market_unique'),
        UniqueConstraint('client_id', name='client_idt_unique')
    )


class Marketplace(Base):
    """Модель таблицы marketplaces."""
    __tablename__ = 'marketplaces'

    marketplace = Column(String(length=255), primary_key=True, nullable=False)
    link = Column(String(length=1000), nullable=False)
    domain = Column(String(length=255), nullable=False)

    markets = relationship("Market", back_populates="marketplace_info")


class Connect(Base):
    """Модель таблицы connects."""
    __tablename__ = 'connects'

    phone = Column(String(length=255), primary_key=True, nullable=False)
    proxy = Column(String(length=255), nullable=False)
    mail = Column(String(length=255), nullable=False)
    token = Column(String(length=255), nullable=False)

    markets = relationship("Market", back_populates="connect_info")

    __table_args__ = (
        UniqueConstraint('phone', 'proxy', name='connects_unique'),
    )


class User(Base):
    """Модель таблицы connects."""
    __tablename__ = 'users'

    user = Column(String(length=255), primary_key=True, nullable=False)
    password = Column(String(length=255), nullable=False)
    name = Column(String(length=255), default=None, nullable=True)
    group = Column(String(length=255), ForeignKey('group_table.group', onupdate="CASCADE"), nullable=False)


class SecretKey(Base):
    """Модель таблицы secret_key."""
    __tablename__ = 'secret_key'

    key = Column(String(length=255), primary_key=True, nullable=False)


class Version(Base):
    """Модель таблицы version."""
    __tablename__ = 'version'

    version = Column(String(length=255), primary_key=True, nullable=False)
    url = Column(String(length=1000), primary_key=True, nullable=False)


class PhoneMessage(Base):
    """Модель таблицы phone_message."""
    __tablename__ = 'phone_message'

    id = Column(Integer, Identity(), primary_key=True)
    user = Column(String(length=255), ForeignKey('users.user', onupdate="CASCADE"), nullable=False)
    phone = Column(String(length=255), ForeignKey('connects.phone', onupdate="CASCADE"), nullable=False)
    marketplace = Column(String(length=255), ForeignKey('marketplaces.marketplace', onupdate="CASCADE"), nullable=False)
    time_request = Column(DateTime, nullable=False)
    time_response = Column(DateTime, default=None, nullable=True)
    message = Column(String(length=255), default=None, nullable=True)

    __table_args__ = (
        UniqueConstraint('time_request', name='phone_message_time_request_unique'),
        UniqueConstraint('time_response', name='phone_message_time_response_unique'),
    )


class Group(Base):
    """Модель таблицы group_table."""
    __tablename__ = 'group_table'

    group = Column(String(length=255), primary_key=True)
    comment = Column(Text, nullable=True)


class GroupMarket(Base):
    """Модель таблицы group_market."""
    __tablename__ = 'group_market'

    group = Column(String(length=255), ForeignKey('group_table.group', onupdate="CASCADE"), primary_key=True)
    marketplace = Column(String(length=255), nullable=False, primary_key=True)
    name_company = Column(String(length=255), nullable=False, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['marketplace', 'name_company'],
            ['markets.marketplace', 'markets.name_company'],
            onupdate="CASCADE"
        ),
    )
