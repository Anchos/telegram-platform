import datetime
import json
import logging
import uuid

from aiohttp import web, WSMsgType

from .client import ClientConnection
from .models import Session
from .pool import Pool


class API(object):
    def __init__(self, pool: Pool):
        self._config = json.loads(open("config.json").read())["API"]
        self._pool = pool
        self.routes = [web.get(self._config["endpoint"], self.process_client)]

    @staticmethod
    def _log(message: str):
        logging.info("[API] %s" % message)

    async def process_client(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connection")

        ws = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None)

        await ws.prepare(request)

        client = ClientConnection(connection=ws)

        async for message in ws:

            if message.type == WSMsgType.TEXT:
                self._log("Client sent %s" % message.data)
                await self._process_message(client, message.data)

            else:
                self._log("Client disconnected")
                await ws.close()

        return ws

    @staticmethod
    async def _validate_message(message: dict) -> str:
        if "id" not in message or not isinstance(message["id"], int):
            return "id is missing"

        if "action" not in message or not isinstance(message["action"], str):
            return "action is missing"

    async def _process_message(self, client: ClientConnection, message: str):
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

        else:
            self._log("%s request" % message["action"])
            await self._pool.send_task(client.session, message)

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
            self._pool.sessions[client.session.session_id] = client

            response["session_id"] = client.session.session_id

        else:
            self._log("Existing session initialisation")

            client.session = Session.get(Session.session_id == message["session_id"])
            response["session_id"] = client.session.session_id

        await client.send_response(response)