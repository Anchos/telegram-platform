import json
import logging

from aiohttp import web, WSMsgType

from .client import ClientConnection
from .models import Client
from .models import Task, update_channels, update_bots, update_stickers
from .worker import WorkerConnection


class Pool(object):
    def __init__(self):
        with open("config.json") as file:
            self.config = json.loads(file.read())["pool"]
            file.close()

        self.routes = [
            web.get(self.config["worker_endpoint"], self.process_worker_connection),
            web.get(self.config["dispatcher_endpoint"], self.process_dispatcher_connection),
            web.get(self.config["auth_endpoint"], self.process_auth_connection),
        ]

        self.pending_tasks = []

        self.dispatcher_bot = None
        self.auth_bot = None

        self.clients = {}
        self.workers = []

    @staticmethod
    def _log(message: str):
        logging.info("[POOL] %s" % message)

    async def send_task(self, client: ClientConnection, task: dict):
        Task.create(
            session=client.session,
            connection_id=client.connection_id,
            data=task,
        )

        if len(self.workers) == 0:
            self._log("No available bots. Caching task")

            self.pending_tasks.append(task)

        else:
            await self.workers[0].send_task(task)
            self.workers.pop(0)

    async def prepare_connection(self, request: web.Request) -> web.WebSocketResponse:
        connection = web.WebSocketResponse(
            heartbeat=self.config["ping_interval"] if self.config["ping_enabled"] else None,
            autoping=True,
        )
        await connection.prepare(request)

        return connection

    async def process_messages(self, connection: web.WebSocketResponse, callback: callable = None, *args):
        async for message in connection:
            if message.type == WSMsgType.TEXT:
                if callback is not None:
                    try:
                        json_message = json.loads(message.data)
                    except:
                        self._log("Invalid JSON")

                        continue

                    await callback(json_message, *args)
            else:
                self._log("Disconnected with exception %s" % connection.exception())

                connection.close()
                break

        self._log("Disconnected")
        self._log(connection.close_code)

    async def process_worker_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New worker connected")

        connection = await self.prepare_connection(request)

        worker = WorkerConnection(connection=connection)
        self.workers.append(worker)

        if len(self.pending_tasks) > 0:
            await worker.send_task(self.pending_tasks.pop())

        await self.process_messages(connection, self.process_worker_message, worker)

        self.workers.remove(worker)

        return connection

    async def process_dispatcher_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New dispatcher connected")

        connection = await self.prepare_connection(request)

        self.dispatcher_bot = connection

        await self.process_messages(connection)

        self.dispatcher_bot = None

        return connection

    async def process_auth_connection(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New auth connected")

        connection = await self.prepare_connection(request)

        self.auth_bot = connection

        await self.process_messages(connection, self.process_auth_message)

        self.auth_bot = None

        return connection

    async def process_worker_message(self, message: dict, worker: WorkerConnection):
        self.workers.append(worker)

        if message["action"] == "UPDATE":
            if message["type"] == "CHANNELS":
                self._log("Updating channels")

                update_channels(message["channels"])

            elif message["type"] == "BOTS":
                self._log("Updating bots")

                update_bots(message["bots"])

            elif message["type"] == "STICKERS":
                self._log("Updating stickers")

                update_stickers(message["stickers"])

            return

        if message["session_id"] not in self.clients:
            self._log("Response ready but session doesn't exist")

        elif message["connection_id"] not in self.clients[message["session_id"]]:
            self._log("Response ready but client doesn't exist")

        else:
            self._log("Response ready and sent to client")

            await self.clients[message["session_id"]][message["connection_id"]].send_response(message)

        if len(self.pending_tasks) > 0:
            await worker.send_task(self.pending_tasks.pop())

    async def process_auth_message(self, message: dict):

        client, created = Client.get_or_create(
            user_id=message["user_id"],
            defaults={
                "first_name": message["first_name"],
                "username": message["username"],
                "language_code": message["language_code"],
                "avatar": message["avatar"],
            }
        )

        if created:
            self._log("New telegram client created")
        else:
            self._log("Existing telegram client")

        if message["session_id"] not in self.clients:
            self._log("Auth ready but session doesn't exist")

        elif message["connection_id"] not in self.clients[message["session_id"]]:
            self._log("Auth ready but client is not connected")

        else:
            self._log("Assigning client to session")
            self.clients[message["session_id"]][message["connection_id"]].session.client = client
            self.clients[message["session_id"]][message["connection_id"]].session.save()

            self._log("Updating all connections with session")
            for connection_id in self.clients[message["session_id"]]:
                self.clients[message["session_id"]][connection_id].session = self.clients[message["session_id"]][
                    message["connection_id"]].session

            self._log("Auth sending to client")
            await self.clients[message["session_id"]][message["connection_id"]].send_response(message)
            self._log("Auth sent to client")
