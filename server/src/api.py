from datetime import datetime, timedelta
import json
import logging
import random
import traceback
from uuid import uuid4

from aiohttp import web
from asyncpgsa import pg
from sqlalchemy.sql import select, outerjoin, insert, desc, update, and_
from sqlalchemy.sql.functions import max

from .client import ClientConnection
from .models import Session, Channel, ChannelAdmin, Client, ChannelSessionAction
from .pool import Pool
from .telegram import Telegram
from .payments import backends

# TODO: make proper message dispatcher pattern implementation
# TODO: input values validity and sanity check
# TODO: Error codes must be enumerated to be translated on every language on the frontend
# TODO: Add endpoint/message for Category model
# TODO: Add DB indexes on fields using on where or on order_by


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
                        bot_token=Telegram.get_bot_token(),
                        user_id=update["from"]["id"],
                    ),
                }

                # TODO: not sure if is that correct, I think update_or_create should be here
                sel_q = select([Client]).where(Client.user_id == update['from']['id'])
                client = await pg.fetchrow(sel_q)
                # TODO: ensure that None is returned when no result found
                if client is None:
                    ins_q = insert(Client).values(user_id=update["from"]["id"],
                                                  first_name=response["first_name"],
                                                  username=response["username"],
                                                  language_code=response["language_code"],
                                                  photo=response["photo"]).returnung(Client.id)
                    client_id = await pg.fetchval(ins_q)
                    self._log("New telegram client created")
                else:
                    client_id = client['id']
                    self._log("Existing telegram client")

                client_dict = {'client_id': client_id,
                               'client_user_id': response['user_id'],
                               'client_first_name': response['first_name'],
                               'client_username': response['username'],
                               'client_language_code': response['language_code'],
                               'client_photo': response['photo']}
                self.pool.clients[text[1]].session.update(client_dict)

                await self.pool.clients[text[1]].send_response(response)

        except Exception as e:
            self._log('Error during auth: %s\n%s' % (e, traceback.format_exc()))

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
        session = None
        if 'session_id' in message:
            sel_q = select([Session, Client], from_obj=[outerjoin(Session, Client)], use_labels=True).where(
                Session.session_id == message['session_id'])
            session = await pg.fetchrow(sel_q)
            # TODO: ensure that None is returned when no result found
        if session is not None:
            # Got session from DB, sent it's info to client
            API._log("Existing session initialization")
            client.session = dict(session.items())
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
            session_dict = {'session_id': str(uuid4()),
                            'expiration': datetime.now() + timedelta(days=2)}
            ins_q = insert(Session).values(**session_dict)
            await pg.fetchrow(ins_q)
            client.session = {'session_' + k: v for k, v in iter(session_dict.items())}

        response["session_id"] = client.session['session_session_id']
        response["connection_id"] = client.connection_id

        await client.send_response(response)

    @staticmethod
    async def fetch_channels(client: ClientConnection, message: dict):
        # TODO: pagination, need to limit response size on the server side
        # TODO: Respect Client's language
        sel_q = select([Channel])

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
            sel_q = sel_q.where(*query_args)

        total = await pg.fetchval(sel_q.count())

        # Apply ordering
        sel_q = sel_q.order_by([desc(Channel.vip), desc(Channel.members), desc(Channel.cost)])

        # Apply Limit/Offset
        sel_q = sel_q.offset(message['offset']).limit(message['count'])

        channels = await pg.fetch(sel_q)

        stat_q = select([max(Channel.members), max(Channel.cost), max(Channel.likes)])
        stats = await pg.fetchrow(stat_q)
        print(list(stats.keys()))

        message["data"] = {
            "items": [dict(x.items()) for x in channels],
            "total": total,
            "max_members": stats['max_members'],
            "max_cost": stats['max_cost'],
            "max_likes": stats['max_likes'],
        }

        await client.send_response(message)

    @staticmethod
    async def fetch_channel(client: ClientConnection, message: dict):
        sel_q = select([Channel]).where(Channel.username == message['username'])
        channel = await pg.fetchrow(sel_q)
        # TODO: ensure that None is returned when no result found
        if channel is None:
            await client.send_error('No such channel')
            return

        message['data'] = dict(channel.items())

        await client.send_response(message)

    @staticmethod
    async def verify_channel(client: ClientConnection, message: dict):
        if not client.is_authorised():
            API._log("Unauthorised client tried to verify a channel")

            await client.send_error("client must login before attempting to verify a channel")
            return

        # TODO: User can be an admin for several channels, message['username'] should be taken into account
        sel_q = select([ChannelAdmin]).where(ChannelAdmin.admin_id == client.session['client_id'])
        channel_admin = await pg.fetchrow(sel_q)
        # TODO: ensure that None is returned when no result found
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

        sel_q = select([Channel]).where(Channel.telegram_id == chat["id"])
        channel = await pg.fetchrow(sel_q)
        # TODO: ensure that None is returned when no result found
        channel_dict = {'telegram_id': chat["id"],
                        'username': "@" + chat["username"],
                        'title': chat["title"],
                        'photo': chat.get("photo", None),
                        'description': chat.get("description", None),
                        'members': chat["members"]}
        if channel is None:
            API._log("Creating new channel")
            ins_q = insert(Channel).values(**channel_dict).returning(Channel.id)
            channel_id = await pg.fetchval(ins_q)
        else:
            API._log("Channel exists")
            channel_id = channel['id']
            upd_q = update(Channel).where(Channel.id == channel_id).values(**channel_dict)
            await pg.fetchrow(upd_q)

        for admin in admins:
            sel_q = select([Client]).where(Client.user_id == admin['id'])
            client = await pg.fetchrow(sel_q)
            # TODO: ensure that None is returned when no result found
            if client is None:
                ins_q = insert(Client).values(user_id=admin["id"],
                                              first_name=admin["first_name"],
                                              username=admin.get("username", None),
                                              photo=admin.get("photo", None)).returning(Client.id)
                admin_id = await pg.fetchval(ins_q)
            else:
                admin_id = client['id']

            ins_q = insert(ChannelAdmin).values(channel_id=channel_id, admin_id=admin_id)
            await pg.fetchrow(ins_q)
            # TODO: check exception when row already exists

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

        sel_q = select([Channel]).where(Channel.username == message["username"])
        channel = await pg.fetchrow(sel_q)
        # TODO: ensure that None is returned when no result found
        if channel is None:
            await client.send_error("channel does not exist")
            return

        # TODO: take user's IP into account to make fake likes adding harder or allow to like only authorized users
        async with pg.transaction() as conn:
            sel_q = select([ChannelSessionAction]).\
                where(and_(ChannelSessionAction.channel_id == channel['id'],
                           ChannelSessionAction.session_id == client.session['id'])).with_for_update()
            channel_session_action = await conn.fetchrow(sel_q)
            # TODO: ensure that None is returned when no result found
            if channel_session_action is None:
                ins_q = insert(ChannelSessionAction).values(channel_id=channel['id'], session_id=client.session['id'],
                                                            like=True)
                await conn.fetchrow(ins_q)
            else:
                if channel_session_action['like']:
                    await client.send_error("channel already liked")
                    return
                upd_q = update(ChannelSessionAction).where(ChannelSessionAction.id == channel_session_action['id']).\
                    values(like=True)
                await conn.fetchrow(upd_q)

            upd_q = update(Channel).where(Channel.id == channel['id']).values(likes=Channel.likes + 1)
            await conn.fetchrow(upd_q)

        API._log(f'Liked channel {message["username"]}')

        await client.send_response({"liked": True})

    @staticmethod
    async def dislike_channel(client: ClientConnection, message: dict):
        if not client.is_initialised():
            API._log("Uninitialised client tried to dislike a channel")

            await client.send_error("client must initialise before attempting to dislike a channel")
            return

        sel_q = select([Channel]).where(Channel.username == message["username"])
        channel = await pg.fetchrow(sel_q)
        # TODO: ensure that None is returned when no result found
        if channel is None:
            await client.send_error("channel does not exist")
            return

        # TODO: take user's IP into account to make fake likes adding harder or allow to like only authorized users
        # TODO: There is an error - can't undo like or dislike
        async with pg.transaction() as conn:
            sel_q = select([ChannelSessionAction]). \
                where(and_(ChannelSessionAction.channel_id == channel['id'],
                           ChannelSessionAction.session_id == client.session['id'])).with_for_update()
            channel_session_action = await conn.fetchrow(sel_q)
            # TODO: ensure that None is returned when no result found
            if channel_session_action is None:
                ins_q = insert(ChannelSessionAction).values(channel_id=channel['id'],
                                                            session_id=client.session['id'],
                                                            like=False)
                await conn.fetchrow(ins_q)
            else:
                if not channel_session_action['like']:
                    await client.send_error("channel already disliked")
                    return
                upd_q = update(ChannelSessionAction).where(ChannelSessionAction.id == channel_session_action['id']). \
                    values(like=False)
                await conn.fetchrow(upd_q)

            upd_q = update(Channel).where(Channel.id == channel['id']).values(likes=Channel.likes - 1)
            await conn.fetchrow(upd_q)

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
