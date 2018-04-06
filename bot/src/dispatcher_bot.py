import asyncio
import json
import logging

from .base_bot import BaseBot
from .telegram_bot import TelegramBot
from .telegram_client import TelegramClient


class DispatcherBot(BaseBot):
    def __init__(self):
        super().__init__(self.process_message)
        with open("config.json") as file:
            self._config.update(json.loads(file.read())["dispatcher"])

        self._pool_url = "http://{0}:{1}{2}".format(
            self._config["pool_host"],
            self._config["pool_port"],
            self._config["pool_endpoint"],
        )

    @staticmethod
    def _log(message: str):
        logging.info("[DISPATCHER BOT] %s" % message)

    def run(self):
        super().run()
        asyncio.get_event_loop().run_forever()

    async def process_message(self, message: dict):
        if message["action"] == "DISPATCH":

            if message["type"] == "telegram_bot":
                TelegramBot().run()

            elif message["type"] == "telegram_client":
                TelegramClient().run()
