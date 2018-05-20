import json
import logging

import peewee
from aiohttp import web, WSMsgType

from .models import Client, Channel


class Pool(object):
    def __init__(self):
        with open("config.json") as file:
            self.config = json.loads(file.read())["pool"]
            file.close()

        self.routes = [
            web.get(self.config["update_endpoint"], self.process_update_connection),
            web.get(self.config["dispatcher_endpoint"], self.process_dispatcher_connection),
            web.get(self.config["auth_endpoint"], self.process_auth_connection),
        ]

        self.pending_tasks = []

        self.dispatcher_bot = None
        self.auth_bot = None
        self.update_bot = None

        self.clients = {}
        self.workers = []

    @staticmethod
    def _log(message: str):
        logging.info("[POOL] %s" % message)

    async def prepare_connection(self, request: web.Request) -> web.WebSocketResponse:
        connection = web.WebSocketResponse(
            heartbeat=self.config.get("ping_interval", None),
            autoping=True,
        )
        await connection.prepare(request)

        return connection

    async def process_messages(self, connection: web.WebSocketResponse, callback: callable = None, *args):
        async for message in connection:
            if message.type == WSMsgType.TEXT:
                if callback is not None:
                    try:
                        json_message = json.loads(message.data)
                    except:
                        self._log("Invalid JSON")

                        continue

                    await callback(json_message, *args)
            else:
                self._log("Disconnected with exception %s" % connection.exception())

                connection.close()
                break

        self._log("Disconnected")
        self._log(connection.close_code)

    async def process_dispatcher_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New dispatcher bot connected")

        connection = await self.prepare_connection(request)

        self.dispatcher_bot = connection

        await self.process_messages(connection, self.process_dispatcher_message)

        self.dispatcher_bot = None

        return connection

    async def process_dispatcher_message(self, message: dict):
        pass

    async def process_auth_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New auth bot connected")

        connection = await self.prepare_connection(request)

        self.auth_bot = connection

        await self.process_messages(connection, self.process_auth_message)

        self.auth_bot = None

        return connection

    async def process_auth_message(self, message: dict):
        client, created = Client.get_or_create(
            user_id=message["user_id"],
            defaults={
                "first_name": message["first_name"],
                "username": message["username"],
                "language_code": message["language_code"],
                "photo": message["photo"],
            }
        )

        if created:
            self._log("New telegram client created")
        else:
            self._log("Existing telegram client")

        if message["session_id"] not in self.clients:
            self._log("Auth ready but session doesn't exist")

        elif message["connection_id"] not in self.clients[message["session_id"]]:
            self._log("Auth ready but client is not connected")

        else:
            self._log("Assigning client to session")
            self.clients[message["session_id"]][message["connection_id"]].session.client = client
            self.clients[message["session_id"]][message["connection_id"]].session.save()

            self._log("Updating all connections with session")
            for connection_id in self.clients[message["session_id"]]:
                self.clients[message["session_id"]][connection_id].session = \
                    self.clients[message["session_id"]][message["connection_id"]].session

            self._log("Auth sending to client")
            await self.clients[message["session_id"]][message["connection_id"]].send_response(message)
            self._log("Auth sent to client")

    async def process_update_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New update bot connected")

        connection = await self.prepare_connection(request)

        self.update_bot = connection

        await self.process_messages(connection, self.process_update_message)

        self.update_bot = None

        return connection

    async def process_update_message(self, message: dict):
        if message["action"] == "UPDATE":
            if message["type"] == "CHANNEL":
                try:
                    channel = Channel.get(Channel.username == message["channel"]["username"])
                    self._log("Channel exists")
                except peewee.DoesNotExist:
                    self._log("Creating new channel")
                    channel = Channel()

                channel.username = message["channel"]["username"]
                channel.telegram_id = message["channel"]["telegram_id"]
                channel.title = message["channel"]["title"]
                channel.photo = message["channel"]["photo"]
                channel.description = message["channel"]["description"]
                channel.members = message["channel"]["members"]

                channel.save()

                self._log("Updated channel %s" % channel.username)
