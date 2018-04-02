import peewee

from .db import db


class Client(peewee.Model):
    user_id = peewee.PrimaryKeyField(unique=True)

    class Meta:
        database = db


class Session(peewee.Model):
    session_id = peewee.CharField(unique=True, null=False)
    expiration = peewee.DateTimeField(null=False)
    client = peewee.ForeignKeyField(Client, null=True)

    @staticmethod
    def exists(session_id: str) -> bool:
        return Session.select().where(Session.session_id == session_id).exists()

    class Meta:
        database = db


class Task(peewee.Model):
    session = peewee.ForeignKeyField(Session, null=False)
    data = peewee.TextField(null=False)
    completed = peewee.BooleanField(default=False, null=False)

    @staticmethod
    def get_uncompleted() -> list:
        return [x.data for x in Task.select(Task.data).where(Task.completed == False)]

    class Meta:
        database = db


db.create_tables([Client, Session, Task])
