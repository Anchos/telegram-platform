import peewee
from playhouse import shortcuts

from .db import db


class Client(peewee.Model):
    user_id = peewee.IntegerField(unique=True)
    first_name = peewee.CharField()
    username = peewee.CharField(null=True)
    language_code = peewee.CharField()
    photo = peewee.CharField(null=True)

    class Meta:
        database = db


class Session(peewee.Model):
    session_id = peewee.CharField(unique=True)
    expiration = peewee.DateTimeField()
    client = peewee.ForeignKeyField(Client, null=True)

    @staticmethod
    def exists(session_id: str) -> bool:
        return Session.select().where(Session.session_id == session_id).exists()

    class Meta:
        database = db


class Task(peewee.Model):
    session = peewee.ForeignKeyField(Session)
    connection_id = peewee.CharField(unique=False)
    data = peewee.TextField()
    completed = peewee.BooleanField(default=False)

    class Meta:
        database = db


class Channel(peewee.Model):
    name = peewee.CharField()
    link = peewee.CharField(unique=True)
    photo = peewee.CharField(null=True)
    category = peewee.CharField()
    description = peewee.TextField(null=True)
    members = peewee.IntegerField(default=0)
    members_growth = peewee.IntegerField(default=0)
    views = peewee.IntegerField(default=0)
    views_growth = peewee.IntegerField(default=0)
    views_per_post = peewee.IntegerField(default=0)

    @staticmethod
    def get_like_by_name(name: str) -> list:
        return Channel.select().where(Channel.name ** name)

    def serialize(self) -> dict:
        return shortcuts.model_to_dict(self)

    class Meta:
        database = db


class Bot(peewee.Model):
    name = peewee.CharField()
    link = peewee.CharField(unique=True)
    photo = peewee.CharField(null=True)
    category = peewee.CharField(null=True)
    description = peewee.TextField(null=True)

    def serialize(self) -> dict:
        return shortcuts.model_to_dict(self)

    class Meta:
        database = db


class Sticker(peewee.Model):
    name = peewee.CharField()
    link = peewee.CharField(unique=True)
    photo = peewee.CharField(null=True)
    category = peewee.CharField(null=True)
    installs = peewee.IntegerField(default=0)
    language = peewee.CharField(null=True)

    def serialize(self) -> dict:
        return shortcuts.model_to_dict(self)

    class Meta:
        database = db


def update_channels(channels: list):
    Channel.insert_many(channels).execute()


def update_bots(bots: list):
    Bot.insert_many(bots).execute()


def update_stickers(stickers: list):
    Sticker.insert_many(stickers).execute()


db.create_tables([
    Client,
    Session,
    Task,
    Channel,
    Bot,
    Sticker
])
