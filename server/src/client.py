import json
import logging

from aiohttp import web, WSMsgType


class ClientConnection(object):
    def __init__(self):
        self.connection = None
        self.connection_id = None
        self.session = None

        from .api import API

        self.actions = {
            "INIT": API.init,
            "FETCH_CHANNELS": API.fetch_channels,
            "FETCH_CHANNEL": API.fetch_channel,
            "VERIFY_CHANNEL": API.verify_channel,
            "UPDATE_CHANNEL": API.update_channel,
        }

    @staticmethod
    def _log(message: str):
        logging.info("[CLIENT] %s" % message)

    async def send_response(self, response: dict):
        try:
            await self.connection.send_json(response)
        except Exception as e:
            self._log("Failed to send message %s" % e)

    async def send_error(self, error: str):
        await self.send_response({"error": error})

    async def prepare_connection(self, request: web.Request) -> web.WebSocketResponse:
        connection = web.WebSocketResponse(
            heartbeat=10,
            autoping=True,
        )
        await connection.prepare(request)
        self.connection = connection

        return connection

    async def process_connection(self):
        async for message in self.connection:
            if message.type == WSMsgType.TEXT:
                try:
                    message = json.loads(message.data)
                except ValueError:
                    self._log("Invalid JSON")

                    self.send_error("invalid JSON")
                    continue
                await self.process_message(message)

            else:
                self._log("Disconnected with exception %s" % self.connection.exception())

                self.connection.close()
                break

        self._log("Disconnected %s" % self.connection.close_code)

    async def process_message(self, message: dict):
        action = self.actions.get(message["action"], None)
        if action is None:
            self._log("No such action %s" % message["action"])
            await self.send_error("no such action")
        else:
            await action(client=self, message=message)
