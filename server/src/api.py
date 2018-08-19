from datetime import datetime, timedelta
import json
import logging
import random
from uuid import uuid4

from aiohttp import web

from .client import ClientConnection
from .models import Session, Channel, ChannelAdmin, Client, Category, ChannelSessionAction
from .pool import Pool
from .telegram import Telegram
from .payments import backends

# TODO: make proper message dispatcher pattern implementation


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
        # TODO: Logs should include client's session ID and IP
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
        # TODO: Need to implement some throttling on init method to prevent brute-force attack
        response = {
            "id": message["id"],
            "action": message["action"],
            "expires_in": 172800,
        }

        # TODO: check expiration or implement deletion
        session = await Session.async_get(message['session_id']) if 'session_id' in message else None
        if session is not None:
            # Got session from DB, sent it's info to client
            API._log("Existing session initialization")
            client.session = session
            user_id = client.session['client_user_id'] if 'client_user_id' in client.session else None
            if user_id is not None:
                await client.send_response({
                    "action": "AUTH",
                    "user_id": client.session['client_user_id'],
                    "first_name": client.session['client_first_name'],
                    "username": client.session['client_username'],
                    "language_code": client.session['client_language_code'],
                    "photo": client.session['client_photo'],
                })
        else:
            # Session is not found, need to generate one
            API._log("New session init")
            # TODO: there is a possibility that UUID will match with existing one, need to try to generate the new one
            client.session = {'session_id': str(uuid4()),
                              'session_expiration': datetime.now() + timedelta(days=2)}
            await Session.async_insert(**client.session)

        response["session_id"] = client.session['session_id']
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

        if "likes" in message:
            query_args.append(Channel.likes.between(message["likes"][0], message["likes"][1]))

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
        max_likes = Channel.select(peewee.fn.MAX(Channel.likes)).scalar()

        message["data"] = {
            "items": [x.serialize() for x in channels],
            "categories": [{"category": x.name, "count": x.count} for x in categories],
            "total": total,
            "max_members": max_members,
            "max_cost": max_cost,
            "max_likes": max_likes,
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
        if not client.is_authorised():
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
    async def like_channel(client: ClientConnection, message: dict):
        if not client.is_initialised():
            API._log("Uninitialised client tried to like a channel")

            await client.send_error("client must initialise before attempting to like a channel")
            return

        try:
            channel = Channel.get(Channel.username == message["username"])
        except Channel.DoesNotExist:
            await client.send_error("channel does not exist")
            return

        channel_session_action, created = ChannelSessionAction.get_or_create(
            channel=channel,
            session=client.session,
            defaults={
                "like": True
            }
        )

        if not created and channel_session_action.like:
            await client.send_error("channel already liked")
            return

        if not channel_session_action.like:
            channel_session_action.like = True
            channel_session_action.save()

        channel.likes += 1
        channel.save()

        API._log(f'Liked channel {message["username"]}')

        await client.send_response({"liked": True})

    @staticmethod
    async def dislike_channel(client: ClientConnection, message: dict):
        if not client.is_initialised():
            API._log("Uninitialised client tried to dislike a channel")

            await client.send_error("client must initialise before attempting to dislike a channel")
            return

        try:
            channel = Channel.get(Channel.username == message["username"])
        except Channel.DoesNotExist:
            await client.send_error("channel does not exist")
            return

        channel_session_action, created = ChannelSessionAction.get_or_create(
            channel=channel,
            session=client.session,
            defaults={
                "like": False
            }
        )

        if not created and not channel_session_action.like:
            await client.send_error("channel already disliked")
            return

        if channel_session_action.like:
            channel_session_action.like = False
            channel_session_action.save()

        channel.likes -= 1
        channel.save()

        API._log(f'Disliked channel {message["username"]}')

        await client.send_response({"disliked": True})

    @staticmethod
    async def prepare_payment(client: ClientConnection, message: dict):
        # Get backend from factory -> return redirection URL
        backend = backends.get("inter_kassa")
        backend.prepare_payment()

        await client.send_error("Stub payment response")

    @staticmethod
    async def process_payment(client: ClientConnection, message: dict):
        """
        This method is only needed for payments which use redirect payment flow

        Get needed backend from factory and process payment
        Grab all data from front-end callback from payment system
        """
        backend = backends.get("inter_kassa")
        backend.process_payment()
        await client.send_error("Stub payment process response")
