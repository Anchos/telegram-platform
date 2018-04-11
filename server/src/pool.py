import json
import logging

from aiohttp import web, WSMsgType

from .bot import BotConnection
from .client import ClientConnection
from .models import Task


class Pool(object):
    def __init__(self):
        file = open("config.json")
        self._config = json.loads(file.read())["pool"]
        file.close()

        self.routes = [web.get(self._config["endpoint"], self.process_bot_connection)]
        self._pending_tasks = Task.get_uncompleted()
        self._log("Pending tasks %s" % self._pending_tasks)

        self.clients = {}
        self._bots = []

    @staticmethod
    def _log(message: str):
        logging.info("[POOL] %s" % message)

    def _get_optimal_bot(self) -> BotConnection:
        self._bots.sort(key=lambda x: x.tasks, reverse=True)
        self._bots[0].tasks += 1

        return self._bots[0]

    async def send_task(self, client: ClientConnection, task: dict):
        Task.create(
            session=client.session,
            connection_id=client.connection_id,
            data=task,
        )

        if len(self._bots) == 0:
            self._log("No available bots. Caching task")
            await client.send_error("no available bots")
            self._pending_tasks.append(task)

        else:
            await self._get_optimal_bot().send_task(task)

    async def broadcast(self, message: str):
        for bot in self._bots:
            try:
                await bot.send_json(message)
            except:
                self._log("Bot disconnected due to error")
                self._bots.remove(bot)

    async def send_pending_tasks(self, bot: BotConnection):
        self._log("Sending pending tasks")

        for task in self._pending_tasks:
            await bot.send_task(task)

    async def process_bot_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New bot connected")

        connection = web.WebSocketResponse(
            heartbeat=self._config["ping_interval"] if self._config["ping_enabled"] else None
        )
        await connection.prepare(request)

        bot = BotConnection(connection=connection)
        self._bots.append(bot)

        if len(self._pending_tasks) > 0:
            self.send_pending_tasks(bot)

        async for message in connection:

            if message.type == WSMsgType.text:
                self._log("Bot sent %s" % message.data)

                await self._process_message(message.data)

            else:
                self._log("Bot disconnected")

                await connection.close()
                self._bots.remove(bot)

        return connection

    async def _process_message(self, message: str):
        message = json.loads(message)

        if message["session_id"] not in self.clients:
            self._log("Response ready but session doesn't exist")

        elif message["connection_id"] not in self.clients[message["session_id"]]:
            self._log("Response ready but client doesn't exist")

        else:
            self._log("Response ready and sent to client")
            await self.clients[message["session_id"]][message["connection_id"]].send_response(message)
