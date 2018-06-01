import uuid


class Generator(object):
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def generate_id() -> str:
        pass
