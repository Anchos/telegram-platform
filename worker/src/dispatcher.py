import asyncio
import json
import logging

from .auth_bot import AuthBot
from .base_worker import BaseWorker
from .update_bot import UpdateBot


class Dispatcher(BaseWorker):
    def __init__(self):
        with open("config.json") as file:
            self.config = json.loads(file.read())["dispatcher"]
            file.close()

        super().__init__(self.config["pool_endpoint"])

    @staticmethod
    def _log(message: str):
        logging.info("[DISPATCHER BOT] %s" % message)

    def run(self):
        super().run()

        UpdateBot().run()
        AuthBot().run()

        asyncio.get_event_loop().run_forever()
