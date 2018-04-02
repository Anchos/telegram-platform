import logging

from src.bot import Bot
from src.worker import Worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    worker = Worker()
    bot = Bot(worker)

    worker.run()
    bot.run()
