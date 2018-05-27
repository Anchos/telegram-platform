import datetime
import json
import logging
import random
import uuid

import peewee
from aiohttp import web

from .client import ClientConnection
from .models import Session, Channel, ChannelAdmin
from .pool import Pool


class API(object):
    def __init__(self):
        file = open("config.json")
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

        if message["action"] == "INIT":
            await self.client_init(client, message)
            return

        if client.session is None:
            self._log("Attempt to call actions without INIT")

            await client.send_error("call INIT before calling other actions")
            return

        else:
            message["session_id"] = client.session.session_id
            message["connection_id"] = client.connection_id

        if message["action"] == "UPDATE":
            await self.update(message)

        elif message["action"] == "FETCH":
            await self.fetch(client, message)

        elif message["action"] == "VERIFY":
            await self.verify(client, message)

        else:
            self._log("ACTION NOT IMPLEMENTED")

    async def update(self, message: dict):
        await self.pool.update_bot.send_json(message)

    async def client_init(self, client: ClientConnection, message: dict):
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

        await client.send_response({
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
            "session_id": client.session.session_id,
            "connection_id": client.connection_id
        })

    async def fetch(self, client: ClientConnection, message: dict):
        error = self.validate_fetch_message(message)
        if error is not None:
            self._log(error)

            await client.send_error(error)
            return

        if message["type"] == "CHANNELS":
            message["data"] = self.fetch_channels(message)

        elif message["type"] == "CHANNEL":
            message["data"] = self.fetch_channel(message)

        elif message["type"] == "BOTS":
            message["data"] = self.fetch_bots(message)

        elif message["type"] == "STICKERS":
            message["data"] = self.fetch_stickers(message)

        return await client.send_response(message)

    async def verify(self, client: ClientConnection, message: dict):
        if client.session.client is None:
            self._log("Unauthorised client tried to verify a channel")

            await client.send_error("must login before attempting to verify a channel")
            return

        error = self.validate_verify_message(message)
        if error is not None:
            self._log(error)

            await client.send_error(error)
            return

        channel_admin = ChannelAdmin.get_or_none(ChannelAdmin.admin == client.session.client)

        if channel_admin is not None:
            await client.send_response({
                "is_admin": True
            })

            channel_admin.channel.verified = True
            channel_admin.channel.save()

        else:
            await client.send_error("client is not admin")

    def fetch_channels(self, message: dict) -> dict:
        if message["title"] is not "":
            title_query = Channel.title ** "%{0}%".format(message["title"])
        else:
            title_query = Channel.title ** "%"

        if message["category"] is not "":
            category_query = Channel.category == message["category"]
        else:
            category_query = (Channel.category.is_null(True)) | (Channel.category.is_null(False))

        if len(message["members"]) >= 2:
            members_query = Channel.members.between(message["members"][0], message["members"][1])
        else:
            members_query = Channel.members >= 0

        if len(message["cost"]) >= 2:
            cost_query = Channel.cost.between(message["cost"][0], message["cost"][1])
        else:
            cost_query = Channel.cost >= 0

        channels = Channel.select().where(
            title_query,
            category_query,
            members_query,
            cost_query,
        ).offset(message["offset"]).limit(message["count"])

        categories = Channel.select(
            Channel.category,
            peewee.fn.COUNT(peewee.SQL("*"))).group_by(Channel.category)

        total = Channel.select().where(
            title_query,
            category_query,
            members_query,
            cost_query,
        ).count()

        max_members = Channel.select(peewee.fn.MAX(Channel.members)).scalar()
        max_cost = Channel.select(peewee.fn.MAX(Channel.cost)).scalar()

        return {
            "items": [x.serialize() for x in channels],
            "categories": [{"category": x.category, "count": x.count} for x in categories],
            "total": total,
            "max_members": max_members,
            "max_cost": max_cost,
        }

    def fetch_channel(self, message: dict) -> dict:
        try:
            channel = Channel.get(Channel.username == message["username"])
        except peewee.DoesNotExist:
            channel = Channel.select().order_by(peewee.fn.Random()).limit(1)

        return channel.serialize()

    def fetch_bots(self, message: dict) -> list:
        pass

    def fetch_stickers(self, message: dict) -> list:
        pass

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
        if message["type"] == "CHANNELS":
            if "count" not in message or not isinstance(message["count"], int):
                return "count is missing"

            if "offset" not in message or not isinstance(message["offset"], int):
                return "offset is missing"

            if "title" not in message or not isinstance(message["title"], str):
                return "title is missing"

            if "category" not in message or not isinstance(message["category"], str):
                return "category is missing"

            if "members" not in message or not isinstance(message["members"], list):
                return "members is missing"

            if "cost" not in message or not isinstance(message["cost"], list):
                return "cost is missing"

        if message["type"] == "CHANNEL":
            if "username" not in message or not isinstance(message["username"], str):
                return "username is missing"

        elif message["type"] == "BOTS":
            pass

        elif message["type"] == "STICKERS":
            pass

    @staticmethod
    def validate_verify_message(message: dict) -> str:
        if "channel_username" not in message or not isinstance(message["channel_username"], str):
            return "channel_username is missing"

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
