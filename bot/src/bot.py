import json
import logging

from aiohttp import web

from .worker import Worker


class Bot(object):
    def __init__(self, worker: Worker):
        self._config = json.loads(open("config.json").read())["bot"]
        self._app = web.Application()
        self._app.add_routes([
            web.get(self._config["webhook_endpoint"], self._process_update)
        ])
        self.worker = worker

    @staticmethod
    def _log(message: str):
        logging.info("[BOT] %s" % message)

    def run(self):
        self._log("STARTING")

        web.run_app(
            self._app,
            host=self._config["webhook_host"],
            port=self._config["webhook_port"],
        )

    async def _process_update(self, request: web.Request):
        self._log("Telegram sent %s" % request.text())
