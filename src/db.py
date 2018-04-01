import json

import peewee

config = json.loads(open("config.json").read())["DB"]

db = peewee.PostgresqlDatabase(
    database=config["database"],
    user=config["user"],
    password=config["password"],
    host=config["host"],
    port=config["port"]
)

db.connect()
