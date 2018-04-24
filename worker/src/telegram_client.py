import json
import logging

import requests

from .base_worker import BaseWorker


class TelegramClient(BaseWorker):
    def __init__(self):
        with open("config.json") as file:
            self.config = json.loads(file.read())["telegram_client"]
            file.close()

        super().__init__(self.process_message, self.config["pool_endpoint"])

    @staticmethod
    def _log(message: str):
        logging.info("[TELEGRAM CLIENT] %s" % message)

    def run(self):
        super().run()

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
