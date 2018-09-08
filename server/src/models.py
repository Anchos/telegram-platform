# coding: utf-8
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, DECIMAL, func
from sqlalchemy.dialects.postgresql import JSONB, ENUM, MONEY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql import expression

Base = declarative_base()
metadata = Base.metadata


class Bot(Base):
    __tablename__ = 'bot'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), default="")
    username = Column(String(255), default=True)
    photo = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), default="")


class Client(Base):
    __tablename__ = 'client'

    # TODO: remove redundant client ID, User_ID is enough here
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    first_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    balance = Column(DECIMAL(12, 2), nullable=True, default=0.00)  # TODO: obsolete
    language_code = Column(String(2), nullable=True)
    photo = Column(String(255), nullable=True)


class Sticker(Base):
    __tablename__ = 'sticker'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), default="")
    username = Column(String(255), default="")
    photo = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    installs = Column(Integer, default=0)
    language = Column(String(2), nullable=True, default='ru')


class Tag(Base):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    language = Column(String(2), nullable=False, default='ru')


class Channel(Base):
    __tablename__ = 'channel'

    # TODO: remove redundant channel ID, telegram ID is enough here
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    photo = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cost = Column(Integer, nullable=False, default=0)
    language = Column(String(2), nullable=False, default='ru')
    members = Column(Integer, nullable=False, default=0)
    members_growth = Column(Integer, nullable=False, default=0)
    views = Column(Integer, nullable=False, default=0)
    views_growth = Column(Integer, nullable=False, default=0)
    vip = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    category_id = Column(ForeignKey('category.id'))
    likes = Column(Integer, nullable=False, default=0)
    mutual_promotion = Column(Boolean, default=False, nullable=False)

    category = relationship('Category')


class Session(Base):
    __tablename__ = 'session'

    # TODO: remove redundant session ID, session_id is enough here
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, unique=True)
    expiration = Column(DateTime)
    client_id = Column(ForeignKey('client.id'))
    client = relationship('Client')


class ChannelAdmin(Base):
    __tablename__ = 'channeladmin'

    # TODO: multicolumn primary key should be here
    id = Column(Integer, primary_key=True)
    channel_id = Column(ForeignKey('channel.id'), nullable=False)
    admin_id = Column(ForeignKey('client.id'), nullable=False)
    owner = Column(Boolean, nullable=False, server_default=expression.false())
    raw = Column(JSONB)

    admin = relationship('Client')
    channel = relationship('Channel')


class ChannelTag(Base):
    __tablename__ = 'channeltag'

    # TODO: multicolumn primary key should be here
    id = Column(Integer, primary_key=True)
    channel_id = Column(ForeignKey('channel.id'), nullable=False)
    tag_id = Column(ForeignKey('tag.id'), nullable=False)

    channel = relationship('Channel')
    tag = relationship('Tag')


class ChannelSessionAction(Base):
    __tablename__ = 'channelsessionaction'

    # TODO: multicolumn primary key should be here
    id = Column(Integer, primary_key=True)
    channel_id = Column(ForeignKey('channel.id'), nullable=False)
    session_id = Column(ForeignKey("session.id"), nullable=False)
    like = Column(Boolean, nullable=False)

    channel = relationship("Channel")
    session = relationship("Session")
    

class Payment(Base):
    """
    Payments received from processing system
    """
    __tablename__ = 'payment'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, nullable=False)  # Transaction ID from payment processing
    pps = Column(ENUM('interkassa', name='pps'), nullable=False)  # Payment processing system
    status = Column(ENUM('processing', 'ok', 'fail', name='status'), nullable=False)
    amount = Column(MONEY, nullable=False)  # Amount refunded to our account
    currency = Column(String(3), nullable=False)  # 3-chars currency code, USD, EUR, RUB, UAH etc
    processed_at = Column(DateTime)  # Filled when status is set to 'ok' or 'fail'
    data = Column(JSONB)  # raw message from payment processing
    __table_args__ = (
        UniqueConstraint('transaction_id', 'pps')
    )


class Offer(Base):
    """
    Offers that we provide to our clients, like "7 days of channel pinned on main page"
    """
    __tablename__ = 'offer'

    id = Column(Integer, primary_key=True)
    price_rub = Column(MONEY, nullable=False)  # Price in RUB
    price_usd = Column(MONEY, nullable=False)  # Price in USD
    price_eur = Column(MONEY, nullable=False)  # Price in EUR
    pin_main_days = Column(Integer)  # Pinned on the main page, days
    pin_category_days = Column(Integer)  # Pinned on the category page, days
    related_days = Column(Integer)  # Show channel as related on other channels page, days
    # TODO: add bumps
    # TODO: add premiums


class Order(Base):
    """
    Client's order. Can contain multiple offers, but all for single channel.
    Payment process:
      1) User choose the offers that he likes
      2) User initiates order creation, choose currency and payment system
      3) We redirect user to payment gateway using order ID
      4) User pays, payment processing system notifies us about payment via special endpoint
      5) We receive notification from PPS, create entry in Payment table
      6) Find out order it's been made for, set payment_id for it
      7) Apply all of the offers that included to order (from OrderOffer table)
    """
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    client_id = Column(ForeignKey('client.id'), nullable=False)  # Client who made an order
    channel_id = Column(ForeignKey('channel.id'), nullable=False)  # For that channel
    created = Column(DateTime, server_default=func.now())  # Order creation time
    payment_id = Column(ForeignKey('payment.id'))  # Payment for this order


class OrderOffer(Base):
    """
    Array of offers that client purchased in the order
    """
    __tablename__ = 'order_offer'

    order_id = Column(ForeignKey('order.id'), primary_key=True)  # What order owns the entry
    offer_id = Column(ForeignKey('offer.id'), primary_key=True)  # What offer is included
    count = Column(Integer, nullable=False, server_default=1)  # Count of similar offers
