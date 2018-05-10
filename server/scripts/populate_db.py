import asyncio
import time

import aiohttp


async def main():
    server_connection = await aiohttp.ClientSession().ws_connect(
        url="http://159.65.126.202:5000/client",
        autoping=True,
    )

    file = open("usernames.txt")
    channels = file.readlines()
    file.close()

    for channel in channels:
        await server_connection.send_json({
            "id": 0,
            "action": "UPDATE",
            "type": "CHANNEL",
            "channel": "@" + channel.strip()
        })
        time.sleep(1)
        break

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
