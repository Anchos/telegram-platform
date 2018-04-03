import logging

from src.api import API
from src.dispatcher import Dispatcher
from src.pool import Pool
from src.server import Server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    server = Server()

    pool = Pool()
    dispatcher = Dispatcher()
    api = API(pool, dispatcher)

    server.add_routes(pool.routes)
    server.add_routes(api.routes)
    server.add_routes(dispatcher.routes)

    server.run()
