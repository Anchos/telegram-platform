import marshmallow

from marshmallow.validate import Length


class GenericRequest(marshmallow.Schema):
    id = marshmallow.fields.Integer(required=True)
    action = marshmallow.fields.String(required=True)


class InitRequest(GenericRequest):
    session_id = marshmallow.fields.String(required=False)


class FetchChannelsRequest(GenericRequest):
    title = marshmallow.fields.String(required=False)
    category = marshmallow.fields.String(required=False,
                                         )
    count = marshmallow.fields.Integer(required=False, missing=10)
    offset = marshmallow.fields.Integer(required=False, missing=0)
    members = marshmallow.fields.List(
        required=False,
        cls_or_instance=marshmallow.fields.Integer(),
        validate=Length(equal=2))
    cost = marshmallow.fields.List(
        required=False,
        cls_or_instance=marshmallow.fields.Integer(),
        validate=Length(equal=2))


class FetchChannelRequest(GenericRequest):
    username = marshmallow.fields.String(required=True)


class VerifyChannelRequest(GenericRequest):
    username = marshmallow.fields.String(required=True)


class UpdateChannelRequest(GenericRequest):
    username = marshmallow.fields.String(required=True)
