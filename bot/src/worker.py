import asyncio
import json
import logging

import aiohttp


class Worker(object):
    def __init__(self):
        with open("config.json") as file:
            self._config = json.loads(file.read())["worker"]
        self._pool_url = "http://{0}:{1}{2}".format(
            self._config["pool_host"],
            self._config["pool_port"],
            self._config["pool_endpoint"],
        )
        self.connection = None

        self._log("Pool URL: %s" % self._pool_url)

    @staticmethod
    def _log(message: str):
        logging.info("[WORKER] %s" % message)

    def run(self):
        self._log("STARTING")

        loop = asyncio.get_event_loop()
        loop.create_task(self.connect_to_pool())

    async def send_to_pool(self, message: dict):
        await self.connection.send_json(message)

    async def connect_to_pool(self):
        self.connection = await aiohttp.ClientSession().ws_connect(self._pool_url)

        async for message in self.connection:
            if message.type == aiohttp.WSMsgType.TEXT:
                self._log("Server sent %s" % message.data)
