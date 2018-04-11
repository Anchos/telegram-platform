import json
import logging

from .base_bot import BaseBot


class TelegramClient(BaseBot):
    def __init__(self, config: dict = None):
        super().__init__(self.process_message)
        if config is not None:
            self._config = config
        else:
            with open("config.json") as file:
                self._config.update(json.loads(file.read())["telegram_bot"])
                file.close()

    @staticmethod
    def _log(message: str):
        logging.info("[TELEGRAM CLIENT] %s" % message)

    def run(self):
        super().run()
        """После этой строки запуск всяких серверов или клиентов"""

    async def process_message(self, message: dict):
        pass
        """Здесь обработка сообщений от центрального сервера"""
