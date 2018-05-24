import asyncio
import logging

from src.auth_bot import AuthBot
from src.update_bot import UpdateBot
from src.verify_bot import VerifyBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(lineno)d %(message)s")

if __name__ == "__main__":
    UpdateBot().run()
    AuthBot().run()
    VerifyBot().run()

    asyncio.get_event_loop().run_forever()
