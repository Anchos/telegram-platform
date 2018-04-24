import datetime
import json
import logging
import random
import uuid

from aiohttp import web

from .client import ClientConnection
from .models import Session
from .models import Task
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

            await client.send_error(error)
            return

        self._log("%s request" % message["action"])

        if message["action"] == "INIT":
            await self.client_init(client, message)

        elif message["action"] == "FETCH":
            await self.fetch(client, message)

        elif message["action"] == "DISPATCH":
            await self.pool.dispatcher_bot.send_json(message)

        else:
            self._log("ACTION NOT IMPLEMENTED")

    @staticmethod
    def validate_message(message: dict) -> str:
        if "id" not in message or not isinstance(message["id"], int):
            return "id is missing"

        if "action" not in message or not isinstance(message["action"], str):
            return "action is missing"

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

    async def send_task(self, client: ClientConnection, task: dict):
        Task.create(
            session=client.session,
            connection_id=client.connection_id,
            data=task,
        )

        if len(self.pool.workers) == 0:
            self._log("No available bots. Caching task")

            self.pool.pending_tasks.append(task)

        else:
            await self.pool.workers[0].send_task(task)
            self.pool.workers.pop(0)

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

    async def fetch(self, client: ClientConnection, message: dict):
        message["session_id"] = client.session.session_id
        message["connection_id"] = client.connection_id
        await self.send_task(client, message)
