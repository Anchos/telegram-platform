import json
import logging

from aiohttp import web, WSMsgType


class Dispatcher(object):
    def __init__(self):
        with open("config.json") as file:
            self._config = json.loads(file.read())["dispatcher"]
            file.close()

        self.routes = [web.get(self._config["endpoint"], self.process_dispatcher_connection)]
        self._dispatcher_connection = None

    @staticmethod
    def _log(message: str):
        logging.info("[DISPATCHER] %s" % message)

    async def process_dispatcher_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New dispatcher connected")

        connection = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None,
            receive_timeout=self._config["receive_timeout"] if self._config["ping_enabled"] else None,
        )
        await connection.prepare(request)

        self._dispatcher_connection = connection

        async for message in connection:
            if message.type == WSMsgType.text:
                self._log("Dispatcher Bot sent %s" % message.data)

            else:
                self._log("Dispatcher Bot disconnected")

        return connection

    async def dispatch(self, message: dict):
        if self._dispatcher_connection is None:
            self._log("No dispatchers available")

        else:
            await self._dispatcher_connection.send_json(message)
