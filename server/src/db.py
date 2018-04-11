import json

import peewee

with open("config.json") as file:
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
