import json
import logging

from aiohttp import web

from .db import Task
from .pool import Pool


class API(object):
    def __init__(self, pool: Pool):
        self._config = json.loads(open("config.json").read())["API"]

        self._app = web.Application()
        self._app.add_routes([
            web.get("/tasks", self.get_tasks),
            web.post("/tasks", self.add_tasks),
        ])

        self._pool = pool

    def run(self):
        """Starts aiohttp HTTP server at host and port specified in config"""

        logging.info("[API] Starting")

        web.run_app(
            self._app,
            host=self._config["host"],
            port=self._config["port"],
        )

    async def get_tasks(self, request: web.Request) -> web.Response:
        logging.info("[API] GET TASKS")
        task = Task.get()
        return web.Response(text=task.data)

    async def add_tasks(self, request: web.Request) -> web.Response:
        logging.info("[API] NEW TASK")

        self._pool.send_task("TEST TASK")

        return web.Response(text="OK")
