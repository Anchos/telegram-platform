import datetime
import json
import logging
import random

import peewee
from aiohttp import web

from .client import ClientConnection
from .generator import Generator
from .models import Session, Channel, ChannelAdmin, Client
from .pool import Pool
from .telegram import Telegram
from .validation import MessageValidator


class API(object):
    def __init__(self):
        file = open("config.json")
        self.config = json.loads(file.read())["API"]
        file.close()

        self.pool = Pool()

        self.routes = [
            web.get(self.config["client_endpoint"], self.client_request),
            web.get(self.config["bot_endpoint"], self.telegram_request)
        ]

    @staticmethod
    def _log(message: str):
        logging.info("[API] %s" % message)

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
        self._log("Telegram sent %s" % await request.text())

        update = json.loads(await request.text())["message"]

        try:
            text = update["text"].split(" ")
            command = text[0]

            if command == "/start":
                response = {
                    "action": "AUTH",
                    "type": "EVENT",
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
            self._log("Error during auth: %s" % e)

        return web.Response()

    @staticmethod
    async def init(client: ClientConnection, message: dict):
        error = MessageValidator.validate_init(message)
        if error is not None:
            await client.send_error(error)
            return

        response = {
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
        }

        if not Session.exists(message["session_id"]):
            API._log("New session initialisation")

            client.session = Session.create(
                session_id=Generator.generate_uuid(),
                expiration=datetime.datetime.now() + datetime.timedelta(days=2)
            )

        else:
            API._log("Existing session initialisation")

            client.session = Session.get(Session.session_id == message["session_id"])

            if client.session.client is not None:
                response.update({
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
        error = MessageValidator.validate_fetch_channels(message)
        if error is not None:
            await client.send_error(error)
            return

        if message["title"] is not "":
            title_query = Channel.title ** "%{0}%".format(message["title"])
        else:
            title_query = Channel.title ** "%"

        if message["category"] is not "":
            category_query = Channel.category == message["category"]
        else:
            category_query = (Channel.category.is_null(True)) | (Channel.category.is_null(False))

        if len(message["members"]) >= 2:
            members_query = Channel.members.between(message["members"][0], message["members"][1])
        else:
            members_query = Channel.members >= 0

        if len(message["cost"]) >= 2:
            cost_query = Channel.cost.between(message["cost"][0], message["cost"][1])
        else:
            cost_query = Channel.cost >= 0

        channels = Channel.select().where(
            title_query,
            category_query,
            members_query,
            cost_query,
        ).offset(message["offset"]).limit(message["count"])

        categories = Channel.select(
            Channel.category,
            peewee.fn.COUNT(peewee.SQL("*"))).group_by(Channel.category)

        total = Channel.select().where(
            title_query,
            category_query,
            members_query,
            cost_query,
        ).count()

        max_members = Channel.select(peewee.fn.MAX(Channel.members)).scalar()
        max_cost = Channel.select(peewee.fn.MAX(Channel.cost)).scalar()

        return {
            "items": [x.serialize() for x in channels],
            "categories": [{"category": x.category, "count": x.count} for x in categories],
            "total": total,
            "max_members": max_members,
            "max_cost": max_cost,
        }

    @staticmethod
    async def fetch_channel(client: ClientConnection, message: dict):
        error = MessageValidator.validate_fetch_channel(message)
        if error is not None:
            await client.send_error(error)
            return

        try:
            channel = Channel.get(Channel.username == message["username"])
        except peewee.DoesNotExist:
            channel = Channel.select().order_by(peewee.fn.Random()).limit(1)

        return channel.serialize()

    @staticmethod
    async def verify_channel(client: ClientConnection, message: dict):
        error = MessageValidator.validate_verify_channel(message)
        if error is not None:
            await client.send_error(error)
            return

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
        error = MessageValidator.validate_update_channel(message)
        if error is not None:
            await client.send_error(error)
            return

        response = await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChat",
            payload={"chat_id": message["username"]}
        )

        if "result" not in response:
            API._log("Channel does not exist")

            client.send_error("channel does not exist")

        else:
            API._log("Channel exists")

        chat = response["result"]

        API._log("Chat info: %s" % chat)

        chat["members"] = (await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChatMembersCount",
            payload={"chat_id": message["username"]}
        ))["result"]

        API._log("Members count: %s" % chat["members"])

        admins = (await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChatAdministrators",
            payload={"chat_id": message["username"]}
        ))["result"]

        API._log("Admins: %s" % admins)

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

        chat["photo"] = await Telegram.get_telegram_file(
            bot_token=Telegram.get_bot_token(),
            file_id=chat["photo"]["big_file_id"]
        )

        API._log("Photo: %s" % chat["photo"])

        API._log("Fetched channel %s" % chat["username"])

        try:
            channel = Channel.get(Channel.telegram_id == chat["id"])

            API._log("Channel exists")

        except peewee.DoesNotExist:
            API._log("Creating new channel")

            channel = Channel()

        channel.telegram_id = chat["id"]
        channel.username = "@" + chat["username"]
        channel.title = chat["title"]
        channel.photo = chat["photo"]
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

        API._log("Updated channel %s" % channel.username)
