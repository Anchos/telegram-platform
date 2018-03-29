from aiohttp import web


class Client(object):
    def __init__(self, connection: web.WebSocketResponse, user_id: int = 0, session_id: str = ""):
        self.connection = connection
        self.session_id = session_id
        self.user_id = user_id

    async def send_response(self, response: dict):
        await self.connection.send_json(response)

    async def send_error(self, error: str):
        await self.connection.send_json({
            "error": error
        })
