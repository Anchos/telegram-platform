import json
import logging
import multiprocessing

from aiohttp import web

from .base_bot import BaseBot


class TelegramBot(BaseBot):
    def __init__(self, config: dict = None):
        super().__init__(self.process_message)
        self._config = config if config is not None else json.loads(open("config.json").read())["telegram_bot"]
        self._app = web.Application()
        self._app.add_routes([web.get(self._config["webhook_endpoint"], self._process_update)])

    @staticmethod
    def _log(message: str):
        logging.info("[TELEGRAM BOT] %s" % message)

    def run(self):
        super().run()

        multiprocessing.Process(target=web.run_app, kwargs={
            "app": self._app,
            "host": self._config["webhook_host"],
            "port": self._config["webhook_port"],
        })

    async def _process_update(self, request: web.Request):
        self._log("Telegram sent %s" % request.text())

    async def process_message(self, message: dict):
        pass
