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
        self._log("Webhook setup: %s" % response.json())

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

    def send_telegram_request(self, method, payload) -> dict:
        response = requests.post(
            url="https://api.telegram.org/bot{0}/{1}".format(self._config["bot_token"], method),
            data=payload,
        )

        self._log("Telegram API response: %s" % response.json())

        return response.json()

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

                avatar_file_id = self.send_telegram_request(
                    "getUserProfilePhotos",
                    {"user_id": update["from"]["id"], "limit": 1},
                )["result"]["photos"][0][2]["file_id"]

                file_path = self.send_telegram_request(
                    "getFile",
                    {"file_id": avatar_file_id}
                )["result"]["file_path"]

                response["avatar"] = "https://api.telegram.org/file/bot{0}/{1}".format(
                    self._config["bot_token"],
                    file_path,
                )

                await self.send_to_server(response)
        except Exception as e:
            self._log(str(e))

        return web.Response()

    async def process_message(self, message: dict):
        if message["action"] == "FETCH":
            if message["type"] == "CHANNELS":
                channels = requests.post("https://tgstat.ru/en/channels/list").json()["items"]["list"]

                for x in range(len(channels)):
                    channels[x] = {
                        "name": channels[x]["title"],
                        "link": channels[x]["username"],
                        "photo": channels[x]["photo"],
                        "category": channels[x]["category"],
                        "members": channels[x]["members"],
                        "members_growth": channels[x]["members_growth"],
                        "views": channels[x]["views"],
                        "views_growth_percent": channels[x]["views_growth_percent"],
                        "views_per_post": channels[x]["views_per_post"],
                    }

                    message["data"] = {
                        "channels": channels
                    }

                await self.send_to_server(message)

            elif message["type"] == "BOTS":
                bots = requests.get("https://storebot.me/api/bots?list=top&languages=russian&count=100").json()

                for x in range(len(bots)):
                    bots[x] = {
                        "name": bots[x]["name"],
                        "link": bots[x]["link"],
                        "photo": bots[x]["photo"].replace("[WIDTH]x[HEIGHT]", "120x120") if "photo" in bots[
                            x] else None,
                        "description": bots[x]["description"] if "description" in bots[x] else None,
                        "category": bots[x]["categoryId"] if "categoryId" in bots[x] else None,
                    }

                message["data"] = {
                    "bots": bots
                }

                await self.send_to_server(message)

            elif message["type"] == "STICKERS":
                stickers = requests.get(
                    "https://tlgrm.ru/stickers?page=0&ajax=true",
                    headers={"X-Requested-With": "XMLHttpRequest"}).json()["data"]

                for x in range(len(stickers)):
                    stickers[x] = {
                        "name": stickers[x]["name"],
                        "link": stickers[x]["link"],
                        "count": stickers[x]["count"],
                        "installs": stickers[x]["installs"],
                        "lang": stickers[x]["lang"],
                    }

                message["data"] = {
                    "stickers": stickers
                }

                await self.send_to_server(message)
