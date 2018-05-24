"""
DEPRECIATED, DO NOT USE / REFACTOR / TOUCH
"""

import json
import logging

import requests

from .base_worker import BaseWorker


class TelegramClient(BaseWorker):
    def __init__(self):
        file = open("config.json")
        self.config = json.loads(file.read())["telegram_client"]
        file.close()

        super().__init__(self.config["pool_endpoint"], self.process_message)

    @staticmethod
    def _log(message: str):
        logging.info("[TELEGRAM CLIENT] %s" % message)

    def run(self):
        super().run()

    async def process_message(self, message: dict):
        if message["action"] == "UPDATE":
            if message["type"] == "BOTS":
                bots = requests.get("https://storebot.me/api/bots?list=top&languages=russian&count=10000").json()

                for x in range(len(bots)):
                    bots[x] = {
                        "name": bots[x].get("name", "N/A"),
                        "link": bots[x]["link"],
                        "photo": bots[x]["photo"].replace("[WIDTH]x[HEIGHT]", "120x120") if "photo" in bots[
                            x] else None,
                        "description": bots[x].get("description", None),
                        "category": bots[x].get("categoryId", None)
                    }

                message["bots"] = bots

            elif message["type"] == "STICKERS":
                stickers = []
                last_page = requests.get(
                    "https://tlgrm.ru/stickers?page=1",
                    headers={"X-Requested-With": "XMLHttpRequest"}).json()["last_page"]

                for page in range(1, last_page):

                    stickers_new = requests.get(
                        "https://tlgrm.ru/stickers?page={0}".format(page),
                        headers={"X-Requested-With": "XMLHttpRequest"}).json()["data"]

                    for x in range(len(stickers_new)):
                        stickers_new[x] = {
                            "name": stickers_new[x]["name"],
                            "link": stickers_new[x]["link"],
                            "installs": stickers_new[x]["installs"],
                            "language": stickers_new[x]["lang"],
                        }

                    stickers += stickers_new

                message["stickers"] = stickers

            await self.send_response_to_server(message)
