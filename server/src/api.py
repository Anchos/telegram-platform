import datetime
import json
import logging
import random
import uuid

import peewee
from aiohttp import web

from .client import ClientConnection
from .models import Session, Channel, ChannelAdmin, Client, Category
from .pool import Pool
from .telegram import Telegram


class API(object):
    def __init__(self):
        file = open("config.json")
        self.config = json.loads(file.read())["API"]
        file.close()

        self.pool = Pool()

        self.routes = [
            web.get(self.config["client_endpoint"], self.client_request),
            web.post(self.config["bot_endpoint"], self.telegram_request)
        ]

    @staticmethod
    def _log(message: str):
        logging.info(f"[API] {message}")

    def get_bot_token(self) -> str:
        return random.SystemRandom().choice(self.config["bot_tokens"])

    async def client_request(self, request: web.Request) -> web.WebSocketResponse:
        self._log("New client connected")

        client = ClientConnection()

        connection = await client.prepare_connection(request)
        self.pool.add_client(client)

        await client.process_connection()

        self.pool.remove_client(client)
        return connection

    async def telegram_request(self, request: web.Request) -> web.Response:
        update = json.loads(await request.text())["message"]

        self._log(f"Telegram sent {update}")

        try:
            text = update["text"].split(" ")
            command = text[0]

            if command == "/start":
                response = {
                    "action": "AUTH",
                    "user_id": update["from"]["id"],
                    "first_name": update["from"]["first_name"],
                    "username": update["from"].get("username", None),
                    "language_code": update["from"]["language_code"],
                    "photo": await Telegram.get_user_profile_photo(
                        bot_token=self.config["bot_token"],
                        user_id=update["from"]["id"],
                    ),
                }

                client, created = Client.get_or_create(
                    user_id=update["from"]["id"],
                    defaults={
                        "first_name": response["first_name"],
                        "username": response["username"],
                        "language_code": response["language_code"],
                        "photo": response["photo"],
                    }
                )

                if created:
                    self._log("New telegram client created")
                else:
                    self._log("Existing telegram client")

                self.pool.clients[text[1]].session.client = client

                await self.pool.clients[text[1]].send_response(response)

        except Exception as e:
            self._log(f"Error during auth: {e.with_traceback()}")

        return web.Response()

    @staticmethod
    async def init(client: ClientConnection, message: dict):
        response = {
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
        }

        if "session_id" not in message or not Session.exists(message["session_id"]):
            API._log("New session initialisation")

            client.session = Session.create(
                session_id=str(uuid.uuid4()),
                expiration=datetime.datetime.now() + datetime.timedelta(days=2)
            )

        else:
            API._log("Existing session initialisation")

            client.session = Session.get(Session.session_id == message["session_id"])

            if client.session.client is not None:
                await client.send_response({
                    "action": "AUTH",
                    "user_id": client.session.client.user_id,
                    "first_name": client.session.client.first_name,
                    "username": client.session.client.username,
                    "language_code": client.session.client.language_code,
                    "photo": client.session.client.photo,
                })

        response["session_id"] = client.session.session_id
        response["connection_id"] = client.connection_id

        await client.send_response(response)

    @staticmethod
    async def fetch_channels(client: ClientConnection, message: dict):
        query_args = []

        if "title" in message and message["title"] is not "":
            query_args.append(Channel.title ** f'%{message["title"]}%')

        if "category" in message:
            query_args.append(Channel.category.name == message["category"])

        if "members" in message:
            query_args.append(Channel.members.between(message["members"][0], message["members"][1]))

        if "cost" in message:
            query_args.append(Channel.cost.between(message["cost"][0], message["cost"][1]))

        if len(query_args) > 0:
            channels = Channel.select().where(*query_args).offset(message["offset"]).limit(message["count"])
        else:
            channels = Channel.select().offset(message["offset"]).limit(message["count"])

        # TODO: Refactor this in future(never)
        channels = sorted(
            channels,
            key=lambda channel: (channel.vip, channel.members, channel.cost),
            reverse=True
        )

        categories = Category.select(
            Category.name,
            peewee.fn.COUNT(peewee.SQL("*"))
        ).group_by(Category.name)

        if len(query_args) > 0:
            total = Channel.select().where(*query_args).count()
        else:
            total = Channel.select().count()
        max_members = Channel.select(peewee.fn.MAX(Channel.members)).scalar()
        max_cost = Channel.select(peewee.fn.MAX(Channel.cost)).scalar()

        message["data"] = {
            "items": [x.serialize() for x in channels],
            "categories": [{"category": x.name, "count": x.count} for x in categories],
            "total": total,
            "max_members": max_members,
            "max_cost": max_cost,
        }

        await client.send_response(message)

    @staticmethod
    async def fetch_channel(client: ClientConnection, message: dict):
        try:
            channel = Channel.get(Channel.username == message["username"])
        except Channel.DoesNotExist:
            channel = Channel.select().order_by(peewee.fn.Random()).limit(1)

        message["data"] = channel.serialize()

        await client.send_response(message)

    @staticmethod
    async def verify_channel(client: ClientConnection, message: dict):
        if client.session.client is None:
            API._log("Unauthorised client tried to verify a channel")

            await client.send_error("client must login before attempting to verify a channel")
            return

        channel_admin = ChannelAdmin.get_or_none(ChannelAdmin.admin == client.session.client)

        if channel_admin is not None:
            channel_admin.channel.verified = True
            channel_admin.channel.save()

            await client.send_response({
                "is_admin": True
            })

        else:
            await client.send_error("client is not admin")

    @staticmethod
    async def update_channel(client: ClientConnection, message: dict):
        response = await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChat",
            payload={"chat_id": message["username"]}
        )

        if "result" not in response:
            API._log("Channel does not exist")

            await client.send_error("channel does not exist")
            return

        else:
            API._log("Channel exists")

        chat = response["result"]

        API._log(f"Chat info: {chat}")

        chat["members"] = (await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChatMembersCount",
            payload={"chat_id": message["username"]}
        ))["result"]

        API._log(f'Members count: {chat["members"]}')

        admins = (await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChatAdministrators",
            payload={"chat_id": message["username"]}
        ))

        if "result" in admins:
            admins = admins["result"]

            API._log(f"Admins: {admins}")

            for x in range(len(admins)):
                admins[x] = admins[x]["user"]
                try:
                    API._log(admins[x]["id"])
                    admins[x]["photo"] = await Telegram.get_user_profile_photo(
                        bot_token=Telegram.get_bot_token(),
                        user_id=admins[x]["id"],
                    )
                    API._log(admins[x]["photo"])

                except Exception as e:
                    API._log(str(e))
        else:
            admins = []

        if "photo" in chat:
            chat["photo"] = await Telegram.get_telegram_file(
                bot_token=Telegram.get_bot_token(),
                file_id=chat["photo"]["big_file_id"]
            )

            API._log(f'Photo: {chat["photo"]}')

        API._log(f'Fetched channel @{chat["username"]}')

        try:
            channel = Channel.get(Channel.telegram_id == chat["id"])

            API._log("Channel exists")

        except Channel.DoesNotExist:
            API._log("Creating new channel")

            channel = Channel()

        channel.telegram_id = chat["id"]
        channel.username = "@" + chat["username"]
        channel.title = chat["title"]
        channel.photo = chat.get("photo", None)
        channel.description = chat.get("description", None)
        channel.members = chat["members"]

        channel.save()

        for admin in admins:
            channel_admin = ChannelAdmin()
            channel_admin.channel = channel
            channel_admin.admin, _ = Client.get_or_create(
                user_id=admin["id"],
                defaults={
                    "first_name": admin["first_name"],
                    "username": admin.get("username", None),
                    "photo": admin.get("photo", None),
                }
            )
            channel_admin.save()

        API._log(f"Updated channel {channel.username}")

        await client.send_response({
            "updated": True
        })


    @staticmethod
    def prepare_payment():
        raise NotImplemented("Stub for future payments module")

    @staticmethod
    def process_payment():
        raise NotImplemented("Stub for future payments module")
