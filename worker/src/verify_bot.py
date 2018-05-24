import json
import logging

from .base_worker import BaseWorker
from .common import get_bot_token, send_telegram_request


class VerifyBot(BaseWorker):
    def __init__(self):
        file = open("config.json")
        self.config = json.loads(file.read())["verify_bot"]
        file.close()
        super().__init__(self.config["pool_endpoint"], self.process_message)

    @staticmethod
    def _log(message: str):
        logging.info("[VERIFY BOT] %s" % message)

    def run(self):
        super().run()

    async def process_message(self, message: dict):
        response = await self.verify_channel(
            client_username=message["client_username"],
            channel_username=message["channel_username"],
        )

        self.send_response_to_server(response)

    async def verify_channel(self, client_username: str, channel_username: str) -> dict:
        response = await send_telegram_request(
            bot_token=get_bot_token(),
            method="getChatAdministrators",
            payload={"chat_id": channel_username}
        )

        if "result" not in response:
            return {
                "is_admin": False,
                "error": "channel does not exist",
            }

        admins = response["result"]

        self._log("Channel admins: %s" % admins)
        self._log("Client username: %s" % client_username)

        if client_username in admins:
            self._log("Client in admins list")

            return {
                "is_admin": True
            }

        else:
            self._log("Client not in admins list")

            return {
                "is_admin": False
            }
