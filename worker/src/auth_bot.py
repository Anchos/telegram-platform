import asyncio
import logging
import multiprocessing
import ssl

import requests
from aiohttp import web

from .base_worker import BaseWorker
from .common import *


class AuthBot(BaseWorker):
    def __init__(self):
        with open("config.json") as file:
            self.config = json.loads(file.read())["auth_bot"]
            file.close()

        super().__init__(self.config["pool_endpoint"])

    @staticmethod
    def _log(message: str):
        logging.info("[AUTH BOT] %s" % message)

    def setup_webhook(self):
        response = requests.post(
            url="https://api.telegram.org/bot{0}/setWebhook".format(self.config["bot_token"]),
            data={
                "url": "https://{0}:{1}{2}".format(
                    self.config["webhook_host"],
                    self.config["webhook_port"],
                    self.config["webhook_endpoint"],
                )
            },
            files={"certificate": open(self.config["webhook_public_key"])}
        )

        self._log("Webhook setup: %s" % response.json())

    def run_webhook_listener(self):
        asyncio.set_event_loop(asyncio.new_event_loop())

        super().run()

        self.setup_webhook()

        app = web.Application()
        app.add_routes([web.post(self.config["webhook_endpoint"], self.process_update)])

        ssl_context = ssl.SSLContext()

        ssl_context.load_cert_chain(
            self.config["webhook_public_key"],
            self.config["webhook_private_key"],
        )

        web.run_app(
            app=app,
            host=self.config["webhook_host"],
            port=self.config["webhook_port"],
            ssl_context=ssl_context,
        )

    def run(self):
        multiprocessing.Process(target=self.run_webhook_listener).start()

    async def process_update(self, request: web.Request) -> web.Response:
        self._log("Telegram sent %s" % await request.text())

        update = json.loads(await request.text())["message"]

        try:
            text = update["text"].split(" ")
            command = text[0]

            if command == "/start":
                response = {
                    "action": "AUTH",
                    "type": "EVENT",
                    "session_id": text[1].split("_")[0],
                    "connection_id": text[1].split("_")[1],
                    "user_id": update["from"]["id"],
                    "first_name": update["from"]["first_name"],
                    "username": update["from"]["username"],
                    "language_code": update["from"]["language_code"],
                    "photo": await get_user_profile_photo(
                        bot_token=get_bot_token(),
                        user_id=update["from"]["id"],
                    ),
                }

                await self.send_response_to_server(response)

        except Exception as e:
            self._log(str(e))

        return web.Response()
