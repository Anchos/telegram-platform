# coding: utf-8
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


class Bot(Base):
    __tablename__ = 'bot'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    photo = Column(String(255))
    category = Column(String(255))
    description = Column(Text)


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)


class Client(Base):
    __tablename__ = 'client'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    first_name = Column(String(255), nullable=False)
    username = Column(String(255))
    language_code = Column(String(255), nullable=False)
    photo = Column(String(255))


class Sticker(Base):
    __tablename__ = 'sticker'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    photo = Column(String(255))
    category = Column(String(255))
    installs = Column(Integer, nullable=False)
    language = Column(String(255))


class Tag(Base):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)


class Channel(Base):
    __tablename__ = 'channel'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    photo = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    cost = Column(Integer, nullable=False)
    language = Column(String(255))
    members = Column(Integer, nullable=False)
    members_growth = Column(Integer, nullable=False)
    views = Column(Integer, nullable=False)
    views_in_total = Column(Integer, nullable=False)
    views_growth = Column(Integer, nullable=False)
    vip = Column(Boolean)
    verified = Column(Boolean)
    category_id = Column(ForeignKey('category.id'), index=True)

    category = relationship('Category')


class Session(Base):
    __tablename__ = 'session'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, unique=True)
    expiration = Column(DateTime, nullable=False)
    client_id = Column(ForeignKey('client.id'), index=True)

    client = relationship('Client')


class Channeladmin(Base):
    __tablename__ = 'channeladmin'

    id = Column(Integer, primary_key=True)
    channel_id = Column(ForeignKey('channel.id'), nullable=False, index=True)
    admin_id = Column(ForeignKey('client.id'), nullable=False, index=True)

    admin = relationship('Client')
    channel = relationship('Channel')


class Channeltag(Base):
    __tablename__ = 'channeltag'

    id = Column(Integer, primary_key=True)
    channel_id = Column(ForeignKey('channel.id'), nullable=False, index=True)
    tag_id = Column(ForeignKey('tag.id'), nullable=False, index=True)

    channel = relationship('Channel')
    tag = relationship('Tag')
