class MessageValidator(object):
    @staticmethod
    def validate_general(message: dict) -> str:
        if "id" not in message or not isinstance(message["id"], int):
            return "id is missing"

        elif "action" not in message or not isinstance(message["action"], str):
            return "action is missing"

        elif "type" not in message or not isinstance(message["type"], str):
            return "type is missing"

    @staticmethod
    def validate_init(message: dict) -> str:
        error = MessageValidator.validate_general(message)
        if error is not None:
            return error

        if "session_id" not in message:
            return "session_id is missing"

    @staticmethod
    def validate_fetch_channels(message: dict) -> str:
        error = MessageValidator.validate_general(message)
        if error is not None:
            return error

        if "count" not in message or not isinstance(message["count"], int):
            return "count is missing"

        elif "offset" not in message or not isinstance(message["offset"], int):
            return "offset is missing"

        elif "title" not in message or not isinstance(message["title"], str):
            return "title is missing"

        elif "category" not in message or not isinstance(message["category"], str):
            return "category is missing"

        elif "members" not in message or not isinstance(message["members"], list):
            return "members is missing"

        elif "cost" not in message or not isinstance(message["cost"], list):
            return "cost is missing"

    @staticmethod
    def validate_fetch_channel(message: dict) -> str:
        error = MessageValidator.validate_general(message)
        if error is not None:
            return error

        if "username" not in message or not isinstance(message["username"], str):
            return "username is missing"

    @staticmethod
    def validate_verify_channel(message: dict) -> str:
        error = MessageValidator.validate_general(message)
        if error is not None:
            return error

        if "username" not in message or not isinstance(message["username"], str):
            return "username is missing"

    @staticmethod
    def validate_update_channel(message: dict) -> str:
        error = MessageValidator.validate_general(message)
        if error is not None:
            return error

        if "username" not in message or not isinstance(message["username"], str):
            return "username is missing"
