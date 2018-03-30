import json
import logging

from aiohttp import web, WSMsgType

from .bot import Bot
from .db import Task


class Pool(object):
    def __init__(self):
        self._config = json.loads(open("config.json").read())["pool"]
        self.routes = [
            web.get(self._config["endpoint"], self.process_bot)
        ]
        self._pending_tasks = Task.get_uncompleted()
        self._log("Pending tasks %s" % self._pending_tasks)
        self._bots = []

    @staticmethod
    def _log(message):
        logging.info("[POOL] %s" % message)

    def _get_optimal_bot(self) -> Bot:
        """Sort bots by current number of tasks and return the one with least tasks"""

        self._bots.sort(key=lambda x: x.tasks, reverse=True)
        self._bots[0].tasks += 1

        return self._bots[0]

    async def send_task(self, task: str):
        """Adds new task to DB and sends it to Bot"""

        task = Task.create(completed=False, data=task)

        if len(self._bots) == 0:
            self._log("No bots available. Caching task")
            self._pending_tasks.append(task)

        else:
            bot = self._get_optimal_bot()
            await bot.send_task(task)

    async def broadcast(self, message: str):
        """Sends a message to all connected clients"""

        for client in self._bots:
            try:
                await client.send_json(message)
            except RuntimeError as e:
                self._log(e)
                self._bots.remove(client)
            except ValueError as e:
                self._log(e)

    async def process_bot(self, request: web.Request) -> web.WebSocketResponse:
        """Appends bot to the pool and listens to incoming messages"""

        self._log("New bot connection")

        ws = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None
        )
        await ws.prepare(request)

        bot = Bot(connection=ws)
        self._bots.append(bot)

        if len(self._pending_tasks) > 0:
            self._log("Sending pending tasks")
            for task in self._pending_tasks:
                bot.send_task(task)

        async for message in ws:

            if message.type == WSMsgType.text:
                self._log("Bot send %s" % message.data)
                bot.tasks -= 1

            elif message.type == WSMsgType.CLOSE or message.type == WSMsgType.ERROR:
                self._log("Bot disconnected")
                await ws.close()
                self._bots.remove(bot)

        return ws
