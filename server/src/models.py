import json

import peewee
from playhouse import shortcuts

file = open("config.json")
config = json.loads(file.read())["DB"]
file.close()

db = peewee.PostgresqlDatabase(
    database=config["database"],
    user=config["user"],
    password=config["password"],
    host=config["host"],
    port=config["port"]
)

db.connect()


class BaseModel(peewee.Model):
    def serialize(self) -> dict:
        return shortcuts.model_to_dict(self)

    class Meta:
        database = db


class Client(BaseModel):
    user_id = peewee.IntegerField(unique=True)
    first_name = peewee.CharField(null=True)
    username = peewee.CharField(null=True)
    language_code = peewee.CharField(null=True)
    photo = peewee.CharField(null=True)


class Session(BaseModel):
    session_id = peewee.CharField(unique=True)
    expiration = peewee.DateTimeField()
    client = peewee.ForeignKeyField(Client, null=True)

    @staticmethod
    def exists(session_id: str) -> bool:
        return Session.select().where(Session.session_id == session_id).exists()


class Tag(BaseModel):
    name = peewee.CharField(unique=True)


class Category(BaseModel):
    name = peewee.CharField(default="")


class Channel(BaseModel):
    telegram_id = peewee.BigIntegerField(default=0, unique=True)
    title = peewee.CharField()
    username = peewee.CharField(null=True)
    photo = peewee.CharField(null=True)
    description = peewee.TextField(null=True)
    cost = peewee.IntegerField(default=0)
    language = peewee.CharField(null=True)
    members = peewee.IntegerField(default=0)
    members_growth = peewee.IntegerField(default=0)
    views = peewee.IntegerField(default=0)
    views_growth = peewee.IntegerField(default=0)
    vip = peewee.BooleanField(default=False)
    verified = peewee.BooleanField(default=False)
    category = peewee.ForeignKeyField(Category, null=True)


class ChannelTag(BaseModel):
    channel = peewee.ForeignKeyField(Channel)
    tag = peewee.ForeignKeyField(Tag)


class ChannelAdmin(BaseModel):
    channel = peewee.ForeignKeyField(Channel)
    admin = peewee.ForeignKeyField(Client)


class Bot(BaseModel):
    title = peewee.CharField(default="")
    username = peewee.CharField(default="")
    photo = peewee.CharField(null=True)
    category = peewee.CharField(null=True)
    description = peewee.TextField(null=True)


class Sticker(BaseModel):
    title = peewee.CharField(default="")
    username = peewee.CharField(default="")
    photo = peewee.CharField(null=True)
    category = peewee.CharField(null=True)
    installs = peewee.IntegerField(default=0)
    language = peewee.CharField(null=True)


def update_channels(channels: list):
    Channel.insert_many(channels).execute()


def update_bots(bots: list):
    Bot.insert_many(bots).execute()


def update_stickers(stickers: list):
    Sticker.insert_many(stickers).execute()


db.create_tables([
    Client,
    Session,
    Channel,
    Tag,
    Category,
    ChannelAdmin,
    ChannelTag,
    Bot,
    Sticker
])
