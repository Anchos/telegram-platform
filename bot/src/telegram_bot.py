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

        if config is not None:
            self._config = config
        else:
            file = open("config.json")
            self._config.update(json.loads(file.read())["telegram_bot"])
            file.close()

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
        super().run()
        self.setup_webhook()
        app = web.Application()
        app.add_routes([web.post(self._config["webhook_endpoint"], self.process_update)])

        ssl_context = ssl.SSLContext()

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
        multiprocessing.Process(target=self.run_webhook_listener).start()

    async def process_update(self, request: web.Request) -> web.Response:
        self._log("Telegram sent %s" % await request.text())

        update = json.loads(await request.text())["message"]

        text = update["text"].split(" ")
        command = text[0]

        if command == "/start":
            session_id = text[1].split("_")[0]
            connection_id = text[1].split("_")[1]

            response = {
                "action": "AUTH",
                "type": "EVENT",
                "session_id": session_id,
                "connection_id": connection_id,
                "user_id": update["from"]["id"],
                "first_name": update["from"]["first_name"],
                "username": update["from"]["username"],
                "language_code": update["from"]["language_code"],
            }

            self._log("Response: %s" % response)

            await self.send_to_server(response)

        return web.Response()

    async def process_message(self, message: dict):
        pass