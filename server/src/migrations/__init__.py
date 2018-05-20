import json

from peewee import PostgresqlDatabase
from peewee_migrate.migrator import PostgresqlMigrator

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

