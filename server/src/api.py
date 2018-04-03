import datetime
import json
import logging
import uuid

from aiohttp import web, WSMsgType

from .client import ClientConnection
from .dispatcher import Dispatcher
from .models import Session
from .pool import Pool


class API(object):
    def __init__(self, pool: Pool, dispatcher: Dispatcher):
        self._config = json.loads(open("config.json").read())["API"]
        self._pool = pool
        self._dispatcher = dispatcher
        self.routes = [web.get(self._config["endpoint"], self.process_client_connection)]

    @staticmethod
    def _log(message: str):
        logging.info("[API] %s" % message)

    async def process_client_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connected")

        connection = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None)

        await connection.prepare(request)

        client = ClientConnection(connection=connection)

        async for message in connection:

            if message.type == WSMsgType.TEXT:
                self._log("Client sent %s" % message.data)
                await self._process_message(client, message.data)

            else:
                self._log("Client disconnected")
                await connection.close()

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
        except:
            self._log("Client sent bad JSON")
            await client.send_error("bad JSON")

        error = self._validate_message(message)
        if error is not None:
            self._log("Client sent bad request: %s" % error)
            await client.send_error(error)
            return

        if message["action"] == "INIT":
            self._log("INIT request")

            await self._client_init(client, message)

        elif message["action"] == "DISPATCH":
            self._log("DISPATCH request")

            await self._dispatcher.dispatch(message)

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
