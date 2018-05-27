"""baseline

Revision ID: 022bf3b62746
Revises: 
Create Date: 2018-05-26 22:58:12.627332

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '022bf3b62746'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('bot',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('title', sa.String(length=255), nullable=False),
                    sa.Column('username', sa.String(length=255), nullable=False),
                    sa.Column('photo', sa.String(length=255), nullable=True),
                    sa.Column('category', sa.String(length=255), nullable=True),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('category',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('client',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('first_name', sa.String(length=255), nullable=False),
                    sa.Column('username', sa.String(length=255), nullable=True),
                    sa.Column('language_code', sa.String(length=255), nullable=False),
                    sa.Column('photo', sa.String(length=255), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('user_id')
                    )
    op.create_table('sticker',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('title', sa.String(length=255), nullable=False),
                    sa.Column('username', sa.String(length=255), nullable=False),
                    sa.Column('photo', sa.String(length=255), nullable=True),
                    sa.Column('category', sa.String(length=255), nullable=True),
                    sa.Column('installs', sa.Integer(), nullable=False),
                    sa.Column('language', sa.String(length=255), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('tag',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )
    op.create_table('channel',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
                    sa.Column('title', sa.String(length=255), nullable=False),
                    sa.Column('username', sa.String(length=255), nullable=False),
                    sa.Column('photo', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.Text(), nullable=False),
                    sa.Column('cost', sa.Integer(), nullable=False),
                    sa.Column('language', sa.String(length=255), nullable=True),
                    sa.Column('members', sa.Integer(), nullable=False),
                    sa.Column('members_growth', sa.Integer(), nullable=False),
                    sa.Column('views', sa.Integer(), nullable=False),
                    sa.Column('views_growth', sa.Integer(), nullable=False),
                    sa.Column('vip', sa.Boolean(), nullable=True),
                    sa.Column('verified', sa.Boolean(), nullable=True),
                    sa.Column('category_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('telegram_id')
                    )
    op.create_index(op.f('ix_channel_category_id'), 'channel', ['category_id'], unique=False)
    op.create_table('session',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('session_id', sa.String(length=255), nullable=False),
                    sa.Column('expiration', sa.DateTime(), nullable=False),
                    sa.Column('client_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('session_id')
                    )
    op.create_index(op.f('ix_session_client_id'), 'session', ['client_id'], unique=False)
    op.create_table('channeladmin',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('channel_id', sa.Integer(), nullable=False),
                    sa.Column('admin_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['admin_id'], ['client.id'], ),
                    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_channeladmin_admin_id'), 'channeladmin', ['admin_id'], unique=False)
    op.create_index(op.f('ix_channeladmin_channel_id'), 'channeladmin', ['channel_id'], unique=False)
    op.create_table('channeltag',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('channel_id', sa.Integer(), nullable=False),
                    sa.Column('tag_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ),
                    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_channeltag_channel_id'), 'channeltag', ['channel_id'], unique=False)
    op.create_index(op.f('ix_channeltag_tag_id'), 'channeltag', ['tag_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_channeltag_tag_id'), table_name='channeltag')
    op.drop_index(op.f('ix_channeltag_channel_id'), table_name='channeltag')
    op.drop_table('channeltag')
    op.drop_index(op.f('ix_channeladmin_channel_id'), table_name='channeladmin')
    op.drop_index(op.f('ix_channeladmin_admin_id'), table_name='channeladmin')
    op.drop_table('channeladmin')
    op.drop_index(op.f('ix_session_client_id'), table_name='session')
    op.drop_table('session')
    op.drop_index(op.f('ix_channel_category_id'), table_name='channel')
    op.drop_table('channel')
    op.drop_table('tag')
    op.drop_table('sticker')
    op.drop_table('client')
    op.drop_table('category')
    op.drop_table('bot')
