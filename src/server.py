import json
import logging

from aiohttp import web


class Server(object):
    def __init__(self):
        self._config = json.loads(open("config.json").read())["server"]
        self._app = web.Application()

    @staticmethod
    def _log(message):
        logging.info("[SERVER] %s" % message)

    def run(self):
        self._log("STARTING")

        web.run_app(
            self._app,
            host=self._config["host"],
            port=self._config["port"],
        )

    def add_routes(self, routes):
        self._app.add_routes(routes)
