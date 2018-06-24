"""transaction_model

Revision ID: 38445f43fde0
Revises: 93fbce563c87
Create Date: 2018-06-24 16:33:30.065970

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38445f43fde0'
down_revision = '93fbce563c87'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=5), nullable=False),
        sa.Column('opened', sa.DateTime(), nullable=True),
        sa.Column('closed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('transactions')
