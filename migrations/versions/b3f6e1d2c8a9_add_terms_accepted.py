"""add terms_accepted field

Revision ID: b3f6e1d2c8a9
Revises: a96d0b74b1af
Create Date: 2026-06-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b3f6e1d2c8a9'
down_revision = 'a96d0b74b1af'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('terms_accepted', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('terms_accepted')
