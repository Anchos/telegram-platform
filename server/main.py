import logging

from src.api import API
from src.server import Server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    server = Server()
    api = API()

    server.add_routes(api.pool.routes)
    server.run()
