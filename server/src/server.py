import json
import logging

from aiohttp import web

from .api import API


class Server(object):
    def __init__(self):
        file = open("config.json")
        self._config = json.loads(file.read())["server"]
        file.close()

        self.app = web.Application()
        self.API = API()

        self.app.add_routes(self.API.routes)

    @staticmethod
    def _log(message: str):
        logging.info(f"[SERVER] {message}")

    def run(self):
        self._log("STARTING")

        web.run_app(
            self.app,
            host=self._config["host"],
            port=self._config["port"],
        )