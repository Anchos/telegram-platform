import logging

from src.dispatcher import Dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    dispatcher = Dispatcher()
    dispatcher.run()
