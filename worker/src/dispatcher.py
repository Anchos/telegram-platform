import asyncio
import json
import logging

from .base_worker import BaseWorker
from .telegram_bot import TelegramBot
from .telegram_client import TelegramClient


class Dispatcher(BaseWorker):
    def __init__(self):
        with open("config.json") as file:
            self.config = json.loads(file.read())["dispatcher"]
            file.close()

        super().__init__(self.process_message, self.config["pool_endpoint"])


    @staticmethod
    def _log(message: str):
        logging.info("[DISPATCHER BOT] %s" % message)

    def run(self):
        super().run()
        asyncio.get_event_loop().run_forever()

    @staticmethod
    async def process_message(message: dict):
        if message["action"] == "DISPATCH":

            if message["type"] == "telegram_bot":
                TelegramBot().run()

            elif message["type"] == "telegram_client":
                TelegramClient().run()
