import json
import logging

from .base_worker import BaseWorker
from .common import get_telegram_file, send_telegram_request, get_bot_token


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
        if message["type"] == "CHANNEL":
            message["channel"] = await self.update_channel(message["channel"])

        elif message["type"] == "USER":
            message["user"] = await self.update_user(message["user"])

        await self.send_response_to_server(message)

    async def update_channel(self, chat_id: str) -> dict:
        response = await send_telegram_request(
            bot_token=get_bot_token(),
            method="getChat",
            payload={"chat_id": chat_id}
        )

        if "result" not in response:
            self._log("Channel does not exist")

            return {}

        chat = response["result"]

        members = (await send_telegram_request(
            bot_token=get_bot_token(),
            method="getChatMembersCount",
            payload={"chat_id": chat_id}
        ))["result"]

        self._log("Fetched channel %s" % chat["username"])

        return {
            "telegram_id": chat["id"],
            "title": chat["title"],
            "username": "@" + chat.get("username", "anon4k"),
            "photo": await get_telegram_file(
                bot_token=get_bot_token(),
                file_id=chat["photo"]["big_file_id"]
            ),
            "description": chat.get("description", ""),
            "members": members
        }

    async def update_user(self, username: str) -> dict:
        pass
