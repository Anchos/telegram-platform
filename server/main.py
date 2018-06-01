import logging

from src.server import Server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    Server().run()
