import logging
import multiprocessing

from src.api import API
from src.pool import Pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    pool = Pool()
    API = API(pool)

    multiprocessing.Process(target=pool.run).start()
    multiprocessing.Process(target=API.run).start()
