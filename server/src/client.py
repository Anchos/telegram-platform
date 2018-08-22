import json
import logging

from aiohttp import web, WSMsgType

from .validators import *


class ClientConnection(object):
    def __init__(self):
        self.connection = None
        self.connection_id = None
        self.session = None

        file = open("config.json")
        self.config = json.loads(file.read())["client"]
        file.close()

        from .api import API

        self.actions = {
            "INIT": (API.init, InitRequest),
            "FETCH_CHANNELS": (API.fetch_channels, FetchChannelsRequest),
            "FETCH_CHANNEL": (API.fetch_channel, FetchChannelRequest),
            "VERIFY_CHANNEL": (API.verify_channel, VerifyChannelRequest),
            "UPDATE_CHANNEL": (API.update_channel, UpdateChannelRequest),
            "LIKE_CHANNEL": (API.like_channel, LikeChannelRequest),
            "DISLIKE_CHANNEL": (API.dislike_channel, DislikeChannelRequest),
            "PAYMENT_REQUEST": (API.prepare_payment, None),
            "PAYMENT_PROCESS": (API.process_payment, None),
            "PAYMENT_REQUEST_INTERKASSA": (API.prepare_payment, PaymentPrepareRequest),
            "PAYMENT_PROCESS_INTERKASSA": (API.process_payment, PaymentProcessRequest),
            "LOGOUT": (API.logout, LogoutRequest),
            "GET_CATEGORIES": (API.get_categories, GetCategoriesRequest),
        }

    @staticmethod
    def log(message: str):
        # TODO: Logs should include client's session ID and IP
        logging.info(f"[CLIENT] {message}")

    def is_initialised(self) -> bool:
        return self.session is not None

    def is_authorised(self) -> bool:
        return self.session.get('client_id', None) is not None

    async def send_response(self, response: dict):
        try:
            self.log('=> %s' % response)
            await self.connection.send_json(response)
        except RuntimeError:
            self.log("Connection is not started or closing")
        except ValueError:
            self.log("Data is not serializable object")
        except TypeError:
            self.log("Value returned by dumps param is not str")

    async def send_error(self, error: str):
        await self.send_response({"error": error})

    async def prepare_connection(self, request: web.Request) -> web.WebSocketResponse:
        connection = web.WebSocketResponse(
            heartbeat=self.config["ping_interval"] if self.config["ping_enabled"] else None,
            autoping=True,
        )
        await connection.prepare(request)
        self.connection = connection

        return connection

    async def process_connection(self):
        async for message in self.connection:
            if message.type == WSMsgType.TEXT:
                self.log(f"<= {message.data}")

                try:
                    message = json.loads(message.data)
                except ValueError:
                    self.log("Invalid JSON")

                    await self.send_error("invalid JSON")
                    continue

                await self.process_message(message)
            else:
                self.log(f"Disconnected with exception {self.connection.exception()}")

                self.connection.close()
                break

        self.log(f"Disconnected {self.connection.close_code}")

    async def process_message(self, message: dict):
        errors = GenericRequest().validate(message)
        if errors:
            await self.send_error(errors)
            return

        action, validator = self.actions.get(message["action"], (None, None))
        if action is None:
            self.log(f'No such action {message["action"]}')

            await self.send_error(f'no such action {message["action"]}')
            return
        else:
            self.log(f'Action: {message["action"]}')

            try:
                message = validator().load(message)
            except marshmallow.ValidationError as e:
                await self.send_error(e.messages)
                return

            await action(client=self, message=message)
