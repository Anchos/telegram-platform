from playhouse.migrate import migrate

from migrations import migrator, db
from models import Tag, Category, ChannelTag, ChannelClient, ChannelCategory, Channel


def commit():
    with db.transaction():
        db.create_tables([
            Tag,
            Category,
            ChannelCategory,
            ChannelTag,
            ChannelClient
        ])
        migrate(
            migrator.add_column('channel', 'vip', Channel.vip),
            migrator.add_column('channel', 'verified', Channel.verified),
            migrator.add_column('channel', 'language', Channel.language),
        )


if __name__ == "__main__":
    commit()
