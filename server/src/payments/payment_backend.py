import logging
from abc import ABC, abstractmethod

from .payment_gateway import InterKassaGateway
from ..models import Transaction
from . import config


class PaymentBackend(ABC):
    GATEWAY = None  # type
    NAME = None

    def __init__(self):
        try:
            self._data = config.PAYMENTS_CONFIGURATIONS[f"{self.NAME}_CONFIG"]
        except KeyError:
            logging.warning(f"Cannot instantiate {self.NAME} payment system.")

    @abstractmethod
    def prepare_payment(self):
        pass

    @abstractmethod
    def process_payment(self):
        pass


class InterKassaBackend(PaymentBackend):
    GATEWAY = InterKassaGateway
    NAME = "INTERKASSA"

    def prepare_payment(self):
        pass

    def process_payment(self):
        pass

