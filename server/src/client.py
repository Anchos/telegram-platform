import logging

from aiohttp import web


class ClientConnection(object):
    def __init__(self, connection: web.WebSocketResponse):
        self.connection = connection
        self.connection_id = None
        self.session = None

    @staticmethod
    def _log(message: str):
        logging.info("[CLIENT] %s" % message)

    async def send_response(self, response: dict):
        try:
            await self.connection.send_json(response)
        except:
            self._log("Failed to send message")

    async def send_error(self, error: str):
        await self.send_response({"error": error})
