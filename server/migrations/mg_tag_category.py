import json

import sys

import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from peewee import PostgresqlDatabase
from playhouse.migrate import migrate, PostgresqlMigrator

from src.models import Tag, Category, ChannelTag, ChannelClient, ChannelCategory, Channel

file = open("config.json")
config = json.loads(file.read())["DB"]
file.close()

db = PostgresqlDatabase(
    database=config["database"],
    user=config["user"],
    password=config["password"],
    host=config["host"],
    port=config["port"]
)

migrator = PostgresqlMigrator(db)


def commit():
    with db.transaction():
        db.create_tables([
            Tag,
            Category,
            ChannelCategory,
            ChannelTag,
            ChannelClient
        ])
        migrate(
            migrator.add_column('channel', 'vip', Channel.vip),
            migrator.add_column('channel', 'verified', Channel.verified),
            migrator.add_column('channel', 'language', Channel.language),
        )


if __name__ == "__main__":
    commit()
