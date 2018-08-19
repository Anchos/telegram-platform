"""user_balance

Revision ID: 1adf997157b1
Revises: 1a4d06caff0b
Create Date: 2018-06-01 14:47:18.216476

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1adf997157b1'
down_revision = '1a4d06caff0b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('client', sa.Column('balance', sa.DECIMAL(precision=12, scale=2), nullable=True))


def downgrade():
    op.drop_column('client', 'balance')
