import logging

from aiohttp import web

from .models import Session


class ClientConnection(object):
    def __init__(self, connection: web.WebSocketResponse, session: Session = None):
        self.connection = connection
        self.session = session

    @staticmethod
    def _log(message: str):
        logging.info("[CLIENT] %s" % message)

    async def send_response(self, response: dict):
        try:
            await self.connection.send_json(response)
        except:
            self._log("Failed to send response")

    async def send_error(self, error: str):
        await self.send_response({"error": error})
