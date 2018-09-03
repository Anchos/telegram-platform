from datetime import datetime, timedelta
import json
import logging
import random
import traceback
from uuid import uuid4

from aiohttp import web
from asyncpgsa import pg
from sqlalchemy import func
from sqlalchemy.sql import select, outerjoin, insert, desc, update, and_, or_, delete
from sqlalchemy.sql.functions import max, count

from .client import ClientConnection
from .models import Session, Channel, ChannelAdmin, Client, ChannelSessionAction, Category, Tag, ChannelTag
from .pool import Pool
from .telegram import Telegram
from .payments import backends

# TODO: make proper message dispatcher pattern implementation
# TODO: input values validity and sanity check
# TODO: Add DB indexes on fields using on where or on order_by
# TODO: Check user session\authorization status


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
        upd = json.loads(await request.text())["message"]

        self._log(f"Telegram sent {upd}")

        try:
            text = upd["text"].split(" ")
            command = text[0]

            if command == "/start":
                response = {
                    "action": "AUTH",
                    "user_id": upd["from"]["id"],
                    "first_name": upd["from"]["first_name"],
                    "username": upd["from"].get("username", None),
                    "language_code": upd["from"]["language_code"],
                    "photo": await Telegram.get_user_profile_photo(
                        bot_token=Telegram.get_auth_bot_token(),
                        user_id=upd["from"]["id"],
                    ),
                }

                # TODO: not sure if is that correct, I think update_or_create should be here
                sel_q = select([Client]).where(Client.user_id == upd['from']['id'])
                client = await pg.fetchrow(sel_q)
                if client is None:
                    ins_q = insert(Client).values(user_id=upd["from"]["id"],
                                                  first_name=response["first_name"],
                                                  username=response["username"],
                                                  language_code=response["language_code"],
                                                  photo=response["photo"]).returning(Client.id)
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

                upd_q = update(Session).where(
                    Session.session_id == self.pool.clients[text[1]].session['session_session_id']
                ).values(client_id=client_id)
                await pg.fetchrow(upd_q)
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
    async def logout(client: ClientConnection, message: dict):
        """
        Disassociate session and telegram user
        :param client:
        :param dict message:
        """
        if client.session.get('client_id', None):
            upd_q = update(Session).where(
                Session.session_id == client.session['session_session_id']
            ).values(client_id=None)
            await pg.fetchrow(upd_q)

            client_dict = {'client_id': None,
                           'client_user_id': None,
                           'client_first_name': None,
                           'client_username': None,
                           'client_language_code': None,
                           'client_photo': None}
            client.session.update(client_dict)

        await client.send_response(message)

    @staticmethod
    async def fetch_channels(client: ClientConnection, message: dict):
        filters = []
        from_obj = Channel

        if message.get('title', None):
            filters.append(or_(Channel.title.ilike(f'%{message["title"]}%'),
                               Channel.description.ilike('%s' % message['title']),
                               func.lower(Tag.name).startswith(message['title'].lower())))
            from_obj = outerjoin(outerjoin(Channel, ChannelTag), Tag)

        if "category_id" in message:
            filters.append(Channel.category_id == message["category_id"])

        if "members" in message:
            filters.append(Channel.members.between(message["members"][0], message["members"][1]))

        if "cost" in message:
            filters.append(Channel.cost.between(message["cost"][0], message["cost"][1]))

        if "likes" in message:
            filters.append(Channel.likes.between(message["likes"][0], message["likes"][1]))

        if "mut_promo" in message:
            filters.append(Channel.mutual_promotion == message['mut_promo'])

        if "verified" in message:
            filters.append(Channel.verified == message['verified'])

        if "partner" in message:
            # TODO: proper premium functions implementation required
            filters.append(Channel.vip == message['partner'])

        if 'language' in message:
            filters.append(Channel.language == message['language'].lower())

        total = await pg.fetchval(select([count(Channel.id.distinct())]).select_from(from_obj).where(and_(*filters)))

        if total:
            sel_q = select([Channel]).select_from(from_obj).where(and_(*filters))

            # Apply ordering
            # TODO: proper premium functions implementation required
            # TODO: manage sorting
            sel_q = sel_q.order_by(desc(Channel.vip), desc(Channel.members), desc(Channel.cost))

            # Apply Limit/Offset
            sel_q = sel_q.offset(message['offset']).limit(message['count'])

            res = await pg.fetch(sel_q)

            # And finally fetch channel tags
            tag_q = select([ChannelTag, Tag]).\
                select_from(outerjoin(ChannelTag, Tag)).\
                where(ChannelTag.channel_id.in_([item['id'] for item in res]))
            tags_raw = await pg.fetch(tag_q)

            # Serialize all the stuff
            tags_dict = {item['id']: [] for item in res}
            for entry in tags_raw:
                tags_dict[entry['channel_id']].append(entry['name'])
            channels = [dict(list(item.items()) + [('tags', tags_dict[item['id']])]) for item in res]
        else:
            channels = []

        stat_q = select([max(Channel.members), max(Channel.cost), max(Channel.likes)])
        stats = await pg.fetchrow(stat_q)

        message["data"] = {
            "items": channels,
            "total": total,
            "max_members": stats['max_1'],
            "max_cost": stats['max_2'],
            "max_likes": stats['max_3'],
        }

        await client.send_response(message)

    @staticmethod
    async def fetch_channel(client: ClientConnection, message: dict):
        sel_q = select([Channel]).select_from(Channel).where(Channel.username == message['username'])
        res = await pg.fetchrow(sel_q)
        if not res:
            await client.send_error(message['id'], 404, 'No such channel')
            return
        channel = dict(res.items())

        sel_q = select([Tag]).select_from(outerjoin(ChannelTag, Tag)).where(ChannelTag.channel_id == channel['id'])
        tags = await pg.fetch(sel_q)
        channel['tags'] = [tag['name'] for tag in tags]

        message['data'] = channel

        await client.send_response(message)

    @staticmethod
    async def verify_channel(client: ClientConnection, message: dict):
        if not client.is_authorized():
            API._log("Unauthorized client tried to verify a channel")
            await client.send_error(message['id'], 401, "client must login before attempting to verify a channel")
            return

        sel_q = select([Channel]).select_from(outerjoin(Channel, ChannelAdmin)).\
            where(and_(ChannelAdmin.admin_id == client.session['client_id'],
                       Channel.username == message['username']))
        channel = await pg.fetchrow(sel_q)
        if not channel:
            await client.send_error(message['id'], 401, 'Only channel admin can do that')
            return

        upd_q = update(Channel).where(Channel.id == channel['id']).values(verified=True)
        await pg.fetchrow(upd_q)

        await client.send_response({'id': message['id'], 'action': message['action']})

    @staticmethod
    async def update_channel(client: ClientConnection, message: dict):
        # Getting general channel info
        response = await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChat",
            params={"chat_id": message["username"]}
        )
        chat = response.get('result', None)
        if not chat:
            await client.send_error(message['id'], 404, "channel does not exist")
            return
        if chat['type'] != 'channel':
            await client.send_error(message['id'], 403, 'Not a channel, but %s' % chat['type'])
            return

        # Get channel members count
        chat["members"] = (await Telegram.send_telegram_request(
            bot_token=Telegram.get_bot_token(),
            method="getChatMembersCount",
            params={"chat_id": message["username"]}
        ))["result"]

        # Get channel admin user list via special public bot
        admins = (await Telegram.send_telegram_request(
            bot_token=Telegram.get_admin_bot_token(),
            method="getChatAdministrators",
            params={"chat_id": message["username"]}
        ))
        admins = admins.get('result', [])
        for admin in admins:
            # Bots are not welcome here
            if admin['user']['is_bot']:
                continue

            user_info = admin['user']
            user_info['photo'] = await Telegram.get_user_profile_photo(
                bot_token=Telegram.get_bot_token(),
                user_id=user_info['id'],
            )

        # Try to get channel photo
        if "photo" in chat:
            chat["photo"] = await Telegram.get_telegram_file(
                bot_token=Telegram.get_bot_token(),
                file_id=chat["photo"]["big_file_id"]
            )

        # Update DB..
        sel_q = select([Channel]).where(Channel.telegram_id == chat["id"])
        channel = await pg.fetchrow(sel_q)
        channel_dict = {'telegram_id': chat["id"],
                        'username': "@" + chat["username"],
                        'title': chat["title"],
                        'photo': chat.get("photo", None),
                        'description': chat.get("description", None),
                        'members': chat["members"]}
        if channel is None:
            ins_q = insert(Channel).values(**channel_dict).returning(Channel.id)
            channel_id = await pg.fetchval(ins_q)
        else:
            channel_id = channel['id']
            upd_q = update(Channel).where(Channel.id == channel_id).values(**channel_dict)
            await pg.fetchrow(upd_q)

        if admins:
            async with pg.transaction() as conn:
                if channel is not None:
                    # Delete current admins for existing channel
                    del_q = delete(ChannelAdmin).where(ChannelAdmin.channel_id == channel_id)
                    await conn.fetchrow(del_q)

                # Populate admin list
                for admin in admins:
                    user_info = admin.pop('user')
                    sel_q = select([Client]).where(Client.user_id == user_info['id'])
                    client = await conn.fetchrow(sel_q)
                    if client is None:
                        ins_q = insert(Client).values(user_id=user_info["id"],
                                                      first_name=user_info["first_name"],
                                                      username=user_info.get("username", None),
                                                      photo=user_info.get("photo", None)).returning(Client.id)
                        admin_id = await conn.fetchval(ins_q)
                    else:
                        admin_id = client['id']

                    ins_q = insert(ChannelAdmin).values(channel_id=channel_id,
                                                        admin_id=admin_id,
                                                        owner=admin['status'] == 'creator',
                                                        raw=admin)
                    await conn.fetchrow(ins_q)

        API._log('%s channel "%s"' % ('Added' if channel is None else 'Updated', chat['username']))

        await client.send_response({'id': message['id'],
                                    'action': message['action']})

    @staticmethod
    async def like_channel(client: ClientConnection, message: dict):
        if not client.is_initialised():
            API._log("Uninitialised client tried to like a channel")

            await client.send_error(message['id'], 401, "client must initialise before attempting to like a channel")
            return

        sel_q = select([Channel]).where(Channel.username == message["username"])
        channel = await pg.fetchrow(sel_q)
        if channel is None:
            await client.send_error(message['id'], 404, "channel does not exist")
            return

        # TODO: take user's IP into account to make fake likes adding harder or allow to like only authorized users
        async with pg.transaction() as conn:
            sel_q = select([ChannelSessionAction]).\
                where(and_(ChannelSessionAction.channel_id == channel['id'],
                           ChannelSessionAction.session_id == client.session['id'])).with_for_update()
            channel_session_action = await conn.fetchrow(sel_q)
            if channel_session_action is None:
                ins_q = insert(ChannelSessionAction).values(channel_id=channel['id'], session_id=client.session['id'],
                                                            like=True)
                await conn.fetchrow(ins_q)
            else:
                if channel_session_action['like']:
                    await client.send_error(message['id'], 403, "channel already liked")
                    return
                upd_q = update(ChannelSessionAction).where(ChannelSessionAction.id == channel_session_action['id']).\
                    values(like=True)
                await conn.fetchrow(upd_q)

            upd_q = update(Channel).where(Channel.id == channel['id']).values(likes=Channel.likes + 1)
            await conn.fetchrow(upd_q)

        API._log(f'Liked channel {message["username"]}')

        await client.send_response({'id': message['id'],
                                    'action': message['action']})

    @staticmethod
    async def dislike_channel(client: ClientConnection, message: dict):
        # TODO: must be merged with like_channel according to new API
        if not client.is_initialised():
            API._log("Uninitialised client tried to dislike a channel")

            await client.send_error(message['id'], 401, "client must initialise before attempting to dislike a channel")
            return

        sel_q = select([Channel]).where(Channel.username == message["username"])
        channel = await pg.fetchrow(sel_q)
        if channel is None:
            await client.send_error(message['id'], 404, "channel does not exist")
            return

        # TODO: take user's IP into account to make fake likes adding harder or allow to like only authorized users
        # TODO: There is an error - can't undo like or dislike
        async with pg.transaction() as conn:
            sel_q = select([ChannelSessionAction]). \
                where(and_(ChannelSessionAction.channel_id == channel['id'],
                           ChannelSessionAction.session_id == client.session['id'])).with_for_update()
            channel_session_action = await conn.fetchrow(sel_q)
            if channel_session_action is None:
                ins_q = insert(ChannelSessionAction).values(channel_id=channel['id'],
                                                            session_id=client.session['id'],
                                                            like=False)
                await conn.fetchrow(ins_q)
            else:
                if not channel_session_action['like']:
                    await client.send_error(message['id'], 403, "channel already disliked")
                    return
                upd_q = update(ChannelSessionAction).where(ChannelSessionAction.id == channel_session_action['id']). \
                    values(like=False)
                await conn.fetchrow(upd_q)

            upd_q = update(Channel).where(Channel.id == channel['id']).values(likes=Channel.likes - 1)
            await conn.fetchrow(upd_q)

        API._log(f'Disliked channel {message["username"]}')

        await client.send_response({'id': message['id'],
                                    'action': message['action']})

    @staticmethod
    async def prepare_payment(client: ClientConnection, message: dict):
        # Get backend from factory -> return redirection URL
        backend = backends.get("inter_kassa")
        backend.prepare_payment()

        await client.send_error(message['id'], 501, "Stub payment response")

    @staticmethod
    async def process_payment(client: ClientConnection, message: dict):
        """
        This method is only needed for payments which use redirect payment flow

        Get needed backend from factory and process payment
        Grab all data from front-end callback from payment system
        """
        backend = backends.get("inter_kassa")
        backend.process_payment()
        await client.send_error(message['id'], 501, "Stub payment process response")

    @staticmethod
    async def get_categories(client: ClientConnection, message: dict):
        """
        Get available channel categories list
        :param client:
        :param dict message:
        """
        # TODO: Depricated
        sel_q = select([Category]).select_from(Category)
        results = await pg.fetch(sel_q)
        message['items'] = [dict(x.items()) for x in results]
        message['total'] = len(results)
        await client.send_response(message)

    @staticmethod
    async def get_tags(client: ClientConnection, message: dict):
        """
        Get available channel tags list
        :param client:
        :param dict message:
        """
        sel_q = select([Tag]).select_from(Tag).order_by(Tag.name).where(Tag.language == message['language']).limit(5)
        if 'name' in message:
            # istartswith analog here
            sel_q = sel_q.where(func.lower(Tag.name).startswith(message['name'].lower()))
        results = await pg.fetch(sel_q)
        message['items'] = [dict(x.items()) for x in results]
        message['total'] = len(results)
        await client.send_response(message)

    @staticmethod
    async def modify_channel(client: ClientConnection, message: dict):
        """
        Get available channel tags list
        :param client:
        :param dict message:
        """
        # Check is user authorized
        if not client.is_authorized():
            await client.send_error(message['id'], 401, "client must login before attempting to modify a channel")
            return

        # Check channel exists in our DB and verified
        # Check user is admin
        sel_q = select([Channel]).\
            select_from(outerjoin(Channel, ChannelAdmin)).\
            where(and_(Channel.username == message['username'],
                       Channel.verified == True,
                       ChannelAdmin.admin_id == client.session['client_id']))
        API._log('DBG: %s' % sel_q)
        res = await pg.fetch(sel_q)
        if not res:
            await client.send_error(message['id'], 404, 'Channel is not found or not verified or user is not admin')
            return
        channel = dict(res.items())

        updated = {}
        # Check category change
        if 'category_id' in message:
            updated['category_id'] = message['category_id']
        # Check mutual promotion changed
        if 'mut_promo' in message:
            updated['mutual_promotion'] = message['mut_promo']
        # Check cost changed
        if 'cost' in message:
            updated['cost'] = message['cost']
        # Check language changed
        if 'language' in message:
            updated['language'] = message['language']
        # Check description changed
        if 'description' in message:
            updated['description'] = message['description']
        # Check tags changed
        if 'tags' in message:
            # TODO: custom tags can be defined for premium channels
            # istartswith analog here
            sel_q = select([Tag]).select_from(Tag).\
                where(func.lower(Tag.name).in_([tag.lower() for tag in message['tags']]))
            API._log('DBG: %s' % sel_q)
            tags = await pg.fetch(sel_q)
            async with pg.transaction() as conn:
                # Delete current tags
                del_q = delete(ChannelTag).where(ChannelTag.channel_id == channel['id'])
                await conn.fetchrow(del_q)
                # Insert new ones
                for tag in tags:
                    ins_q = insert(ChannelTag).values(channel_id=channel['id'], tag_id=tag['id'])
                    await conn.fetchrow(ins_q)
        else:
            # if not changed, just get current ones
            sel_q = select([Tag]).select_from(outerjoin(ChannelTag, Tag)).where(ChannelTag.channel_id == channel['id'])
            tags = await pg.fetch(sel_q)
        channel['tags'] = [tag['name'] for tag in tags]

        if updated:
            upd_q = update(Channel).where(Channel.id == channel['id']).values(**updated)
            await pg.fetchrow(upd_q)
            channel.update(updated)

        # Return channel object
        await client.send_response({'data': channel,
                                    'id': message['id'],
                                    'action': message['action']})
