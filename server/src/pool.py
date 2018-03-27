import json
import logging

from aiohttp import web, WSMsgType

from .db import Task


class Pool(object):
    def __init__(self):
        """Loads config file and initialises aiohttp application."""

        self._config = json.loads(open("config.json").read())["pool"]

        self._app = web.Application()
        self._app.add_routes([web.get("/", self.process_client)])

        self._clients = []

    def run(self):
        """Starts aiohttp websocket server at host and port specified in config"""

        logging.info("[POOL] Starting")
        web.run_app(
            self._app,
            host=self._config["host"],
            port=self._config["port"],
        )

    def send_task(self, task: str):
        """Adds new task to DB and sends it to Bot"""

        self._clients[0].tasks += 1
        self._clients[0].send_task(task)

        Task.create(completed=False, data=task)

    async def broadcast(self, message: str):
        """Sends a message to all connected clients"""

        for client in self._clients:
            try:
                await client.send_json(message)
            except RuntimeError as e:
                logging.info(e)
                self._clients.remove(client)
            except ValueError as e:
                logging.info(e)

    async def process_client(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"]
        )
        await ws.prepare(request)

        client = Client(connection=ws)

        self._clients.append(client)
        self._clients.sort(key=lambda x: x.tasks, reverse=True)

        # Listen for incoming messages
        async for message in ws:
            if message.type == WSMsgType.text:
                logging.info("[POOL] %s" % message.data)
                client.tasks -= 1
            elif message.type == WSMsgType.close:
                logging.info("[POOL] disconnected")
                self._clients.remove(ws)

        return ws


class Client(object):
    def __init__(self, connection: web.WebSocketResponse):
        self._connection = connection
        self.tasks = 0

    async def send_task(self, task: str):
        self._connection.send_json(task)
