import asyncio
import json
import logging

import aiohttp


class BaseBot(object):
    def __init__(self, process_message: callable):
        file = open("config.json")
        self._config = json.loads(file.read())["base_bot"]
        file.close()

        self._pool_url = "http://{0}:{1}{2}".format(
            self._config["pool_host"],
            self._config["pool_port"],
            self._config["pool_endpoint"],
        )
        self._server_connection = None
        self._process_message = process_message

    @staticmethod
    def _log(message: str):
        logging.info("[LINK] %s" % message)

    def run(self):
        self._log("STARTING")

        loop = asyncio.get_event_loop()
        loop.create_task(self.connect_to_server())

    async def send_to_server(self, message: dict):
        await self._server_connection.send_json(message)

    async def connect_to_server(self):
        self._server_connection = await aiohttp.ClientSession().ws_connect(
            url=self._pool_url,

        )

        async for message in self._server_connection:
            if message.type == aiohttp.WSMsgType.TEXT:
                self._log("Server sent %s" % message.data)

                await self._process_message(json.loads(message.data))
