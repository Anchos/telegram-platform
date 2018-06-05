import logging
import random

from .client import ClientConnection


class Pool(object):
    def __init__(self):
        self.clients = {}

    @staticmethod
    def _log(message: str):
        logging.info(f"[POOL] {message}")

    def add_client(self, client: ClientConnection):
        client.connection_id = self.generate_id()
        self.clients[client.connection_id] = client

    def remove_client(self, client: ClientConnection):
        del self.clients[client.connection_id]

    def client_exists(self, client: ClientConnection) -> bool:
        return client.connection_id in self.clients

    def generate_id(self) -> str:
        connection_id = "".join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 8))

        if connection_id in self.clients:
            return self.generate_id()
        else:
            return connection_id
