import asyncio
import json
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

                file_id = (await send_telegram_request(
                    bot_token=self.config["bot_token"],
                    method="getUserProfilePhotos",
                    payload={"user_id": update["from"]["id"], "limit": 1},
                ))["result"]["photos"][0][2]["file_id"]

                response["photo"] = get_telegram_file(
                    bot_token=self.config["bot_token"],
                    file_id=file_id
                )

                await self.send_to_server(response)

        except Exception as e:
            self._log(str(e))

        return web.Response()
