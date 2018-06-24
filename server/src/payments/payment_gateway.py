from abc import ABC, abstractmethod


class PaymentGateway(ABC):
    @abstractmethod
    def resolve_payment(self):
        """
        This method should either make direct payment request or return redirect parameters
        """
        pass


class InterKassaGateway:
    def sign_payload(self):
        pass

    def resolve_payment(self):

        self.make_payment_request()

    def make_payment_request(self):
        pass
