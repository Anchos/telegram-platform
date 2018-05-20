import json
import logging
import random

from .base_worker import BaseWorker
from .common import *


class UpdateBot(BaseWorker):
    def __init__(self):
        file = open("config.json")
        self.config = json.loads(file.read())["update_bot"]
        file.close()
        super().__init__(self.config["pool_endpoint"], self.process_message)

    @staticmethod
    def _log(message: str):
        logging.info("[UPDATE BOT] %s" % message)

    def run(self):
        super().run()

    async def process_message(self, message: dict):
        if message["action"] == "UPDATE":
            if message["type"] == "CHANNEL":
                message["channel"] = await self.update_channel(message["channel"])

            await self.send_to_server(message)

    def get_bot_token(self) -> str:
        return random.SystemRandom().choice(self.config["bot_tokens"])

    async def update_channel(self, chat_id: str) -> dict:
        chat = (await send_telegram_request(
            bot_token=self.get_bot_token(),
            method="getChat",
            payload={"chat_id": chat_id}
        ))["result"]

        members = (await send_telegram_request(
            bot_token=self.get_bot_token(),
            method="getChatMembersCount",
            payload={"chat_id": chat_id}
        ))["result"]
        chat = {
            "telegram_id": chat["id"],
            "title": chat["title"],
            "username": chat["username"],
            "photo": await get_telegram_file(
                bot_token=self.get_bot_token(),
                file_id=chat["photo"]["big_file_id"]
            ),
            "description": chat.get("description", ""),
            "members": members
        }

        self._log("Fetched channel %s" % chat["username"])

        return chat
