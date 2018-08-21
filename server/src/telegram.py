from io import BytesIO
import json
import logging
import random
from urllib.parse import urlencode

import aiohttp

session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
with open('config.json') as f:
    config = json.loads(f.read())['telegram']

# TODO: handle telegram API errors properly, also handle situation when telegram API will be unavailable


class Telegram(object):
    @staticmethod
    def _log(message: str):
        logging.info(f"[TELEGRAM] {message}")

    @staticmethod
    def get_bot_token() -> str:
        return random.SystemRandom().choice(config['bot_tokens'])

    @staticmethod
    def get_auth_bot_token() -> str:
        return config['auth_bot_token']

    @staticmethod
    async def send_telegram_request(bot_token: str, method: str, params: dict) -> dict:
        query = urlencode(params)
        url = f"https://api.telegram.org/bot{bot_token}/{method}?{query}"
        Telegram._log('Calling %s' % url)
        async with session.get(url=url) as response:
            return await response.json()

    @staticmethod
    async def get_user_profile_photo(bot_token: str, user_id: int) -> (str, None):
        resp = await Telegram.send_telegram_request(
            bot_token=bot_token,
            method="getUserProfilePhotos",
            params={"user_id": user_id, "limit": 1},
        )
        Telegram._log('User profile resp: %s' % resp)
        if not resp['ok']:
            return None

        try:
            file_id = resp["result"]["photos"][0][2]["file_id"]
        except IndexError:
            return None

        return await Telegram.get_telegram_file(
            bot_token=bot_token,
            file_id=file_id
        )

    @staticmethod
    async def get_telegram_file(bot_token: str, file_id: id) -> str:
        file_path = (await Telegram.send_telegram_request(
            bot_token=bot_token,
            method="getFile",
            params={"file_id": file_id}
        ))["result"]["file_path"]

        url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        async with session.get(url=url) as response:
            bytes_file = BytesIO(await response.read())

        form = aiohttp.FormData()
        form.add_field("file", bytes_file)

        async with session.post(url="https://imagebin.ca/upload.php", data=form) as response:
            return (await response.text()).split("url:")[1].strip()
