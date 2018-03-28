import json
import logging
import random
import uuid

from aiohttp import web, WSMsgType

from .pool import Pool


class API(object):
    def __init__(self, pool: Pool):
        self._config = json.loads(open("config.json").read())["API"]
        self._pool = pool
        self._sessions = {}
        self.routes = [
            web.get(self._config["endpoint"], self.process_client)
        ]

    @staticmethod
    def _log(message):
        logging.info("[API] %s" % message)

    async def process_client(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connection")

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for message in ws:

            if message.type == WSMsgType.TEXT:
                self._log("Client send %s" % message.data)
                await self._process_message(ws, message.data)

            elif message.type == WSMsgType.CLOSE or message.type == WSMsgType.ERROR:
                self._log("Client disconnected")
                await ws.close()

        return ws

    @staticmethod
    async def _validate_message(message: dict) -> dict:
        response = {}

        if "id" not in message:
            response["error"] = "id is missing"

        if "action" not in message:
            response["error"] = "action is missing"

        return response

    async def _process_message(self, client: web.WebSocketResponse, message: dict):
        try:
            message = json.loads(message)
        except:
            await client.send_json({
                "error": "bad JSON"
            })

        response = await self._validate_message(message)
        if "error" in response:
            self._log("Client send bad request: %s" % response["error"])
            await client.send_json(response)
            return

        if message["action"] == "INIT":
            self._log("INIT request")
            await self._client_init(client, message)
            return

        if message["action"] == "AUTH":
            self._log("AUTH request")
            await self._client_auth(client, message)
            return

    async def _client_init(self, client: web.WebSocketResponse, message: dict):
        response = {
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
        }

        if "session_id" not in message or message["session_id"] not in self._sessions:
            self._log("New client initialisation")

            new_uuid = str(uuid.uuid4())
            new_user_id = self._generate_user_id()

            self._sessions[new_uuid] = {
                "user_id": new_user_id,
                "session_id": new_uuid
            }

            response["session_id"] = new_uuid
            response["user_id"] = new_user_id
        else:
            self._log("Existing client initialisation")

            response["session_id"] = message["session_id"]
            response["user_id"] = self._sessions[message["session_id"]]["user_id"]

        await client.send_json(response)

    async def _client_auth(self, client: web.WebSocketResponse, message: dict):
        response = {
            "id": message["id"],
            "action": message["action"],
        }

        if "session_id" not in message or message["session_id"] not in self._sessions:
            self._log("Bad authentication from client")
            response["user_id"] = None
        else:
            self._log("Successful authentication from client")
            response["user_id"] = self._sessions[message["session_id"]]["user_id"]

        await client.send_json(response)

    def _generate_user_id(self) -> int:
        user_id = random.randint(100000, 999999)

        if len(self._sessions) == 0:
            return user_id

        for session in self._sessions:
            if self._sessions[session] == user_id:
                return self._generate_user_id()

        return user_id
