import json
import logging

from aiohttp import web
from asyncpgsa import pg

from .api import API


async def create_db_pool(app):
    Server._log('Initializing DB connections pool..')
    await pg.init(host=app['db_conf']['host'],
                  port=app['db_conf']['port'],
                  database=app['db_conf']['database'],
                  user=app['db_conf']['user'],
                  password=app['db_conf']['password'],
                  min_size=20,
                  max_size=20)


class Server(object):
    def __init__(self):
        file = open("config.json")
        cfg_json = json.loads(file.read())
        self._config = cfg_json["server"]
        file.close()

        self.app = web.Application()
        self.API = API()

        self.app['db_conf'] = cfg_json['DB']
        self.app.on_startup.append(create_db_pool)
        self.app.add_routes(self.API.routes)

    @staticmethod
    def _log(message: str):
        logging.info(f"[SERVER] {message}")

    def run(self):
        self._log("STARTING")

        web.run_app(
            self.app,
            host=self._config["host"],
            port=self._config["port"],
        )