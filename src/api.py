import json
import logging
import random
import uuid

from aiohttp import web, WSMsgType

from .client import Client
from .pool import Pool


class API(object):
    def __init__(self, pool: Pool):
        self._config = json.loads(open("config.json").read())["API"]
        self._pool = pool
        self._clients = {}
        self.routes = [
            web.get(self._config["endpoint"], self.process_client)
        ]

    @staticmethod
    def _log(message):
        logging.info("[API] %s" % message)

    async def process_client(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connection")

        ws = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None
        )
        await ws.prepare(request)

        client = Client(connection=ws)

        async for message in ws:

            if message.type == WSMsgType.TEXT:
                self._log("Client send %s" % message.data)
                await self._process_message(client, message.data)

            elif message.type == WSMsgType.CLOSE or message.type == WSMsgType.ERROR:
                self._log("Client disconnected")
                await ws.close()

        return ws

    @staticmethod
    async def _validate_message(message: dict) -> str:
        if "id" not in message or not isinstance(message["id"], int):
            return "id is missing"

        if "action" not in message or not isinstance(message["action"], str):
            return "action is missing"

    async def _process_message(self, client: Client, message: dict):
        try:
            message = json.loads(message)
        except:
            await client.send_error("bad JSON")

        error = await self._validate_message(message)
        if error is not None:
            self._log("Client send bad request: %s" % error)
            await client.send_error(error)

        elif message["action"] == "INIT":
            self._log("INIT request")
            await self._client_init(client, message)

        elif message["action"] == "AUTH":
            self._log("AUTH request")
            await self._client_auth(client, message)

        else:
            self._log("%s request" % message["action"])
            await self._pool.send_task(message)

    async def _client_init(self, client: Client, message: dict):
        response = {
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
        }

        if "session_id" not in message or message["session_id"] not in self._clients:
            self._log("New client initialisation")

            client.session_id = str(uuid.uuid4())
            client.user_id = self._generate_user_id()

            self._clients[client.session_id] = client.user_id

            response["session_id"] = client.session_id
            response["user_id"] = client.user_id

        else:
            self._log("Existing client initialisation")

            client.session_id = message["session_id"]
            client.user_id = self._clients[client.session_id]

            response["session_id"] = client.session_id
            response["user_id"] = client.user_id

        await client.send_response(response)

    async def _client_auth(self, client: Client, message: dict):
        response = {
            "id": message["id"],
            "action": message["action"]
        }

        if "session_id" not in message:
            await client.send_error("session_id is missing")
            return

        if message["session_id"] != client.session_id:
            self._log("Bad authentication from client")
            response["user_id"] = None

        else:
            self._log("Successful authentication from client")
            response["user_id"] = client.user_id

        await client.send_response(response)

    def _generate_user_id(self) -> int:
        user_id = random.randint(100000, 999999)

        if len(self._clients) == 0:
            return user_id

        for session_id in self._clients:
            if self._clients[session_id] == user_id:
                return self._generate_user_id()

        return user_id
