import asyncio
import websockets

async def hello(websocket, path):
    id_token = await websocket.recv()
    print(id_token)
    id,token=id_token.split(' ')
    print('ID=%s\nToken=%s'%(id,token))
    answ = id_token
    await websocket.send(answ)

start_server = websockets.serve(hello, '127.0.0.1', 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()