import asyncio

import aiohttp


async def main():
    server_connection = await aiohttp.ClientSession().ws_connect(
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

    for channel in channels:
        await asyncio.sleep(17)

        print("@" + channel.strip())
        await server_connection.send_json({
            "id": 0,
            "action": "UPDATE_CHANNEL",
            "type": "CHANNEL",
            "username": "@" + channel.strip()
        })


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
