import logging

from src.dispatcher_bot import DispatcherBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    dispatcher = DispatcherBot()
    dispatcher.run()
