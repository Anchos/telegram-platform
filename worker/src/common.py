import secrets
from io import BytesIO

import aiohttp


async def send_telegram_request(bot_token: str, method: str, payload: dict) -> dict:
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

    async with session:
        url = "https://api.telegram.org/bot{0}/{1}".format(bot_token, method)
        async with session.get(url=url, data=payload) as response:
            return await response.json()


async def get_telegram_file(bot_token: str, file_id: id) -> str:
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

    async with session:
        url = "https://api.telegram.org/bot{0}/{1}".format(bot_token, "getFile")
        async with session.get(url=url, data={"file_id": file_id}) as response:
            file_path = (await response.json())["result"]["file_path"]

        url = "https://api.telegram.org/file/bot{0}/{1}".format(bot_token, file_path)
        async with session.get(url=url) as response:
            file = BytesIO(await response.read())

        form = aiohttp.FormData(quote_fields=False)
        form.add_field(secrets.token_urlsafe(8), file, filename="file.png", content_type="image/png")
        async with session.post(url="http://telegra.ph/upload", data=form) as response:
            return "https://telegra.ph" + (await response.json())[0]["src"]
