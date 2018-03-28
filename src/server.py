import json
import logging

from aiohttp import web


class Server(object):
    def __init__(self):
        self._config = json.loads(open("config.json").read())["server"]

        self._app = web.Application()

    def run(self):
        logging.info("[SERVER] STARTING")

        web.run_app(
            self._app,
            host=self._config["host"],
            port=self._config["port"],
        )

    def add_routes(self, routes):
        self._app.add_routes(routes)
