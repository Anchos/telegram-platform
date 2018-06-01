import asyncio
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ..src.telegram import Telegram


async def main():
    file = open("../config.json")
    config = json.loads(file.read())["telegram"]
    file.close()

    response = await Telegram.set_webhook(
        bot_token=config["auth_bot_token"],
        url=config["webhook_URL"],
    )

    print(response)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
