import asyncio
import time

import aiohttp


async def main():
    server_connection = await aiohttp.ClientSession().ws_connect(
        # url="http://159.65.126.202:5000/client",
        verify_ssl=False,
        url="https://ws.recursion.ga/client",
        autoping=True,
    )

    file = open("usernames.txt")
    channels = file.readlines()
    file.close()

    await server_connection.send_json({
        "id": 0,
        "action": "INIT",
        "type": "SESSION",
        "session_id": None,
    })

    await server_connection.send_json({
        "id": 0,
        "action": "UPDATE_CHANNEL",
        "type": "CHANNEL",
        "username": "@hcdev",
    })

    time.sleep(60)

    for channel in channels:
        await server_connection.send_json({
            "id": 0,
            "action": "UPDATE_CHANNEL",
            "type": "CHANNEL",
            "username": "@" + channel.strip()
        })
        time.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
