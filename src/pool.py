import json
import logging

from aiohttp import web, WSMsgType

from .db import Task


class Bot(object):
    def __init__(self, connection: web.WebSocketResponse):
        """Creates bot with 0 tasks and provided connection"""

        self._connection = connection
        self.tasks = 0

    async def send_task(self, task: str):
        """Sends a task to the bot in JSON encoded string"""

        await self._connection.send_str(task)


class Pool(object):
    def __init__(self):
        self._config = json.loads(open("config.json").read())["pool"]
        self.routes = [
            web.get("/bot", self.process_bot)
        ]
        self._bots = []

    def _get_optimal_bot(self) -> Bot:
        """Sort bots by current number of tasks and return the one with least tasks"""

        self._bots.sort(key=lambda x: x.tasks, reverse=True)
        self._bots[0].tasks += 1

        return self._bots[0]

    def send_task(self, task: str):
        """Adds new task to DB and sends it to Bot"""

        bot = self._get_optimal_bot()
        bot.send_task(task)

        Task.create(completed=False, data=task)

    async def broadcast(self, message: str):
        """Sends a message to all connected clients"""

        for client in self._bots:
            try:
                await client.send_json(message)
            except RuntimeError as e:
                logging.info(e)
                self._bots.remove(client)
            except ValueError as e:
                logging.info(e)

    async def process_bot(self, request: web.Request) -> web.WebSocketResponse:
        """Appends bot to the pool and listens to incoming messages"""

        ws = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"]
        )
        await ws.prepare(request)

        bot = Bot(connection=ws)
        self._bots.append(bot)

        async for message in ws:

            if message.type == WSMsgType.text:
                logging.info("[POOL] Bot send %s" % message.data)
                bot.tasks -= 1

            elif message.type == WSMsgType.CLOSE or message.type == WSMsgType.ERROR:
                logging.info("[POOL] Bot disconnected")
                await ws.close()
                self._bots.remove(bot)

        return ws
