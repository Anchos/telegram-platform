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
            with open("config.json") as file:
                self._config.update(json.loads(file.read())["telegram_bot"])

        self._pool_url = "http://{0}:{1}{2}".format(
            self._config["pool_host"],
            self._config["pool_port"],
            self._config["pool_endpoint"],
        )

    @staticmethod
    def _log(message: str):
        logging.info("[TELEGRAM BOT] %s" % message)

    def run(self):
        if self._config["bot_mode"] == "webhook":
            multiprocessing.Process(target=self.run_webhook_listener).start()
            self._log("Webhook listener starting")
        elif self._config["bot_mode"] == "local":
            multiprocessing.Process(target=self.run_local_listener).start()
            self._log("Local listener starting")

    #^# Webhook listener
    def run_webhook_listener(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        super().run()
        self.setup_webhook()
        app = web.Application()
        app.add_routes([web.post(self._config["webhook_endpoint"], self.process_update_webhook)])

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
        self._log("Webhook listener ready")
        asyncio.get_event_loop().run_forever()

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

    async def process_update_webhook(self, request: web.Request) -> web.Response:
        self._log("Webhook listener got message")
        await self.process_update(request.text())
        return web.Response()
    #$#

    #^# Local listener
    def run_local_listener(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        super().run()

        #pip3 install "python-telegram-bot"
        from telegram.ext import Updater as telegram_lib_updater, MessageHandler as telegram_lib_handler, Filters as telegram_lib_filters

        updater = telegram_lib_updater(token=self._config["bot_token"])
        handler = telegram_lib_handler((telegram_lib_filters.text | telegram_lib_filters.command), self.local_listener)
        updater.dispatcher.add_handler(handler)
        updater.start_polling(clean=True) #poll_interval=s
        self._log("Local listener ready")
        asyncio.get_event_loop().run_forever()

    def local_listener(self, bot, update):
        self._log("Local listener got message")
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.process_update(json.dumps(update.to_dict())))
        loop.close()
    #$#

    #^# Processing update
    async def process_update(self, update_data):
        self._log("Telegram sent %s" % update_data)

        update_json = json.loads(update_data)["message"]

        await self.send_to_server({
            "session_id": update_json["text"].split(" ")[1],
            "user_id": update_json["from"]["id"],
            "first_name": update_json["from"]["first_name"],
            "username": update_json["from"]["username"]
        })
    #$#

    async def process_message(self, message: dict):
        pass
