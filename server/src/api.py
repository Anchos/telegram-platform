import datetime
import json
import logging
import random
import uuid

import peewee
from aiohttp import web

from .client import ClientConnection
from .models import Session, Channel, Sticker, Bot
from .pool import Pool


class API(object):
    def __init__(self):
        with open("config.json") as file:
            self._config = json.loads(file.read())["API"]
            file.close()

        self.pool = Pool()

        self.pool.routes.append(
            web.get(self.pool.config["client_endpoint"], self.process_client_connection)
        )

    @staticmethod
    def _log(message: str):
        logging.info("[API] %s" % message)

    async def process_client_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connected")

        connection = await self.pool.prepare_connection(request)
        client = ClientConnection(connection)

        await self.pool.process_messages(connection, self.process_client_messages, client)

        self.delete_client(client)

        return connection

    async def process_client_messages(self, message: dict, client: ClientConnection):
        error = self.validate_message(message)
        if error is not None:
            self._log("Client sent bad request: %s" % error)

            return await client.send_error(error)

        self._log("%s request" % message["action"])

        if message["action"] == "DISPATCH":
            await self.dispatch(message)

        elif message["action"] == "INIT":
            await self.client_init(client, message)

        elif message["action"] == "UPDATE":
            await self.update(client, message)

        elif message["action"] == "FETCH":
            await self.fetch(client, message)

        else:
            self._log("ACTION NOT IMPLEMENTED")

    async def dispatch(self, message: dict):
        await self.pool.dispatcher_bot.send_json(message)

    async def client_init(self, client: ClientConnection, message: dict):
        response = {
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
        }

        if "session_id" not in message or not Session.exists(message["session_id"]):
            self._log("New session initialisation")

            client.session = Session.create(
                session_id=str(uuid.uuid4()),
                expiration=datetime.datetime.now() + datetime.timedelta(days=2)
            )

            self.add_client(client)

        else:
            self._log("Existing session initialisation")

            client.session = Session.get(Session.session_id == message["session_id"])

            self.add_client(client)

        response["session_id"] = client.session.session_id
        response["connection_id"] = client.connection_id

        await client.send_response(response)

    async def update(self, client: ClientConnection, message: dict):
        await self.pool.send_task(client, message)

    async def fetch(self, client: ClientConnection, message: dict):
        error = self.validate_fetch_message(message)

        if message["type"] == "CHANNELS_CATEGORIES":
            message["channels_categories"] = self.fetch_channels_categories()

        elif message["type"] == "BOTS_CATEGORIES":
            message["bots_categories"] = self.fetch_bots_categories()

        elif message["type"] == "STICKERS_CATEGORIES":
            message["stickers_categories"] = self.fetch_stickers_categories()

        elif message["type"] == "CHANNELS_CATEGORIES_QUANTITIES":
            message["channels_categories_quantities"] = self.fetch_channels_categories_quantities()

        elif message["type"] == "BOTS_CATEGORIES_QUANTITIES":
            message["bots_categories_quantities"] = self.fetch_bots_categories_quantities()

        elif message["type"] == "STICKERS_CATEGORIES_QUANTITIES":
            message["stickers_categories_quantities"] = self.fetch_stickers_categories_quantities()

        elif error is not None:
            self._log(error)

            return await client.send_error(error)

        if message["type"] == "CHANNELS":
            message["channels"] = self.fetch_channels(message)

        elif message["type"] == "BOTS":
            message["bots"] = self.fetch_bots(message)

        elif message["type"] == "STICKERS":
            message["stickers"] = self.fetch_stickers(message)

        return await client.send_response(message)

    def fetch_channels(self, message: dict) -> list:
        if message["name"] is not "":
            channels = Channel.select().where(
                Channel.name ** message["name"],
                (Channel.members >= message["members"][0]) | (Channel.members <= message["members"][1]),
                Channel.category == message["category"]
            ).offset(message["offset"]).limit(message["count"])

        else:
            channels = Channel.select().where(
                (Channel.members >= message["members"][0]) | (Channel.members <= message["members"][1]),
            ).offset(message["offset"]).limit(message["count"])

        return [x.serialize() for x in channels]

    def fetch_channels_categories(self) -> list:
        categories = Channel.select(Channel.category)

        return [x.category for x in categories]

    def fetch_channels_categories_quantities(self) -> list:
        quantities = Channel.select(
            Channel.category,
            peewee.fn.COUNT(peewee.SQL("*"))).group_by(Channel.category)

        return [(x.category, x.count) for x in quantities]

    def fetch_bots(self, message: dict) -> list:
        bots = Bot.select().where(
            Bot.name ** message["name"],
        ).offset(message["offset"]).limit(message["count"])

        return [x.serialize() for x in bots]

    def fetch_bots_categories(self) -> list:
        categories = Bot.select(Bot.category)

        return [x.category for x in categories]

    def fetch_bots_categories_quantities(self) -> list:
        quantities = Bot.select(
            Bot.category,
            peewee.fn.COUNT(peewee.SQL("*"))).group_by(Bot.category)

        return [(x.category, x.count) for x in quantities]

    def fetch_stickers(self, message: dict) -> list:
        stickers = Sticker.select().where(
            Sticker.name ** message["name"],
        ).offset(message["offset"]).limit(message["count"])

        return [x.serialize() for x in stickers]

    def fetch_stickers_categories(self) -> list:
        categories = Sticker.select(Sticker.category)

        return [x.category for x in categories]

    def fetch_stickers_categories_quantities(self) -> list:
        quantities = Sticker.select(
            Sticker.category,
            peewee.fn.COUNT(peewee.SQL("*"))).group_by(Sticker.category)

        return [(x.category, x.count) for x in quantities]

    @staticmethod
    def validate_message(message: dict) -> str:
        if "id" not in message or not isinstance(message["id"], int):
            return "id is missing"

        elif "action" not in message or not isinstance(message["action"], str):
            return "action is missing"

        elif "type" not in message or not isinstance(message["type"], str):
            return "type is missing"

    @staticmethod
    def validate_fetch_message(message: dict) -> str:
        if "count" not in message or not isinstance(message["count"], int):
            return "count is missing"

        elif "offset" not in message or not isinstance(message["offset"], int):
            return "offset is missing"

        elif "name" not in message or not isinstance(message["name"], str):
            return "name is missing"

        elif "category" not in message or not isinstance(message["category"], str):
            return "category is missing"

        if message["type"] == "CHANNELS":
            if "members" not in message or not isinstance(message["members"], list):
                return "members is missing"

        elif message["type"] == "BOTS":
            pass

        elif message["type"] == "STICKERS":
            if "installs" not in message or not isinstance(message["installs"], int):
                return "installs is missing"

    def generate_id(self) -> str:
        connection_id = "".join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 8))
        for session in self.pool.clients:
            if connection_id in self.pool.clients[session]:
                return self.generate_id()
        return connection_id

    def client_exists(self, client: ClientConnection) -> bool:
        if client.connection_id is None or client.session is None:
            return False

        for session in self.pool.clients:
            if client.connection_id in self.pool.clients[session]:
                return True

        return False

    def add_client(self, client: ClientConnection):
        client.connection_id = self.generate_id()
        if client.session.session_id not in self.pool.clients:
            self.pool.clients[client.session.session_id] = {client.connection_id: client}
        else:
            self.pool.clients[client.session.session_id][client.connection_id] = client

    def delete_client(self, client: ClientConnection):
        if self.client_exists(client):
            self._log("Client was initialised")

            del self.pool.clients[client.session.session_id][client.connection_id]

        else:
            self._log("Client was not initialised")
