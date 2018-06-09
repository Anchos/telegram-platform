import json
import random
import secrets
from io import BytesIO

import aiohttp


class Telegram(object):
    @staticmethod
    def get_bot_token() -> str:
        file = open("config.json")
        bot_tokens = json.loads(file.read())["telegram"]["bot_tokens"]
        file.close()
        return random.SystemRandom().choice(bot_tokens)

    @staticmethod
    async def send_telegram_request(bot_token: str, method: str, payload: dict) -> dict:
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

        async with session:
            url = "https://api.telegram.org/bot{0}/{1}".format(bot_token, method)
            async with session.get(url=url, data=payload) as response:
                return await response.json()

    @staticmethod
    async def get_user_profile_photo(bot_token: str, user_id: int) -> str:
        file_id = (await Telegram.send_telegram_request(
            bot_token=bot_token,
            method="getUserProfilePhotos",
            payload={"user_id": user_id, "limit": 1},
        ))["result"]["photos"][0][2]["file_id"]

        return await Telegram.get_telegram_file(
            bot_token=bot_token,
            file_id=file_id
        )

    @staticmethod
    async def get_telegram_file(bot_token: str, file_id: id) -> str:
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

        file_path = await Telegram.send_telegram_request(
            bot_token=bot_token,
            method="getFile",
            payload={"file_id": file_id}
        )

        async with session:
            url = "https://api.telegram.org/file/bot{0}/{1}".format(bot_token, file_path)
            async with session.get(url=url) as response:
                bytes_file = BytesIO(await response.read())

            form = aiohttp.FormData(quote_fields=False)
            form.add_field(secrets.token_urlsafe(8), bytes_file, filename="file.png", content_type="image/png")
            async with session.post(url="http://telegra.ph/upload", data=form) as response:
                return "https://telegra.ph" + (await response.json())[0]["src"]
