import asyncio
import json
import logging
import multiprocessing
import ssl

import requests
from aiohttp import web

from .base_bot import BaseBot


class TelegramBot(BaseBot):
    def __init__(self, config: dict = None):
        super().__init__(self.process_message)
        self._config = config if config is not None else json.loads(open("config.json").read())["telegram_bot"]

    @staticmethod
    def _log(message: str):
        logging.info("[TELEGRAM BOT] %s" % message)

    def setup_webhook(self):
        response = requests.post(
            url="https://api.telegram.org/bot{0}/setWebhook".format(self._config["bot_token"]),
            data={
                "url": "https://{0}:{1}{2}".format(
                    self._config["webhook_host"],
                    self._config["webhook_port"],
                    self._config["webhook_endpoint"],
                )
            },
            files={"certificate": open(self._config["webhook_public_key"])}
        )
        self._log(response.text)

    def run_webhook_listener(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        app = web.Application()
        app.add_routes([web.post(self._config["webhook_endpoint"], self.process_update)])

        ssl_context = ssl.create_default_context()
        ssl_context.load_cert_chain(
            self._config["webhook_public_key"],
            self._config["webhook_private_key"],
        )

        web.run_app(
            app=app,
            host=self._config["webhook_host"],
            port=self._config["webhook_port"],
            ssl_context=ssl_context,
        )

    def run(self):
        super().run()
        self.setup_webhook()
        multiprocessing.Process(target=self.run_webhook_listener).start()

    async def process_update(self, request: web.Request) -> web.Response:
        self._log("Telegram sent %s" % request.text())

        return web.Response(status=200)

    async def process_message(self, message: dict):
        pass
