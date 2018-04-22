import datetime
import json
import logging
import random
import uuid

from aiohttp import web, WSMsgType

from .client import ClientConnection
from .dispatcher import Dispatcher
from .models import Session
from .pool import Pool


class API(object):
    def __init__(self, pool: Pool, dispatcher: Dispatcher):
        with open("config.json") as file:
            self._config = json.loads(file.read())["API"]
            file.close()

        self._pool = pool
        self._dispatcher = dispatcher

        self.routes = [web.get(self._config["endpoint"], self.process_client_connection)]

    @staticmethod
    def _log(message: str):
        logging.info("[API] %s" % message)

    def generate_id(self) -> str:
        connection_id = "".join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 8))
        for session in self._pool.clients:
            if connection_id in self._pool.clients[session]:
                return self.generate_id()
        return connection_id

    def client_exists(self, client: ClientConnection) -> bool:
        if client.connection_id is None or client.session is None:
            return False

        for session in self._pool.clients:
            if client.connection_id in self._pool.clients[session]:
                return True

        return False

    def add_client(self, client: ClientConnection):
        client.connection_id = self.generate_id()
        if client.session.session_id not in self._pool.clients:
            self._pool.clients[client.session.session_id] = {client.connection_id: client}
        else:
            self._pool.clients[client.session.session_id][client.connection_id] = client

    def delete_client(self, client: ClientConnection):
        if self.client_exists(client):
            self._log("Client was initialised")

            del self._pool.clients[client.session.session_id][client.connection_id]

        else:
            self._log("Client was not initialised")

    async def process_client_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connected")

        connection = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None,
            receive_timeout=self._config["receive_timeout"] if self._config["ping_enabled"] else None,
        )

        await connection.prepare(request)
        client = ClientConnection(connection)

        async for message in connection:
            if message.type == WSMsgType.TEXT:
                self._log("Client sent %s" % message.data)
                await self._process_message(client, message.data)

        self.delete_client(client)
        self._log("Client disconnected")

        return connection

    @staticmethod
    def _validate_message(message: dict) -> str:
        if "id" not in message or not isinstance(message["id"], int):
            return "id is missing"

        if "action" not in message or not isinstance(message["action"], str):
            return "action is missing"

    async def _process_message(self, client: ClientConnection, message: str):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            self._log("Client sent bad JSON")

            await client.send_error("bad JSON")
            return

        error = self._validate_message(message)
        if error is not None:
            self._log("Client sent bad request: %s" % error)

            await client.send_error(error)
            return

        self._log("%s request" % message["action"])

        if message["action"] == "INIT":
            await self._client_init(client, message)

        elif message["action"] == "FETCH":
            await self._fetch(client, message)

        elif message["action"] == "DISPATCH":
            await self._dispatcher.dispatch(message)

        else:
            self._log("%s request" % message["action"])
            self._log("ACTION NOT IMPLEMENTED")

    async def _client_init(self, client: ClientConnection, message: dict):
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

    async def _fetch(self, client: ClientConnection, message: dict):
        message["session_id"] = client.session.session_id
        message["connection_id"] = client.connection_id
        await self._pool.send_task(client, message)
