"""mutual_promo_not_null

Revision ID: 576da1007e5
Revises: 4d35d392c385
Create Date: 2018-08-24 18:55:25.691757

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '576da1007e5'
down_revision = '4d35d392c385'
branch_labels = None
depends_on = None


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('channel', 'mutual_promotion',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('channel', 'mutual_promotion',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    ### end Alembic commands ###
