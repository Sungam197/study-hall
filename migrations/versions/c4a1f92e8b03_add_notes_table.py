"""add notes table

Revision ID: c4a1f92e8b03
Revises: a96d0b74b1af
Create Date: 2026-06-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4a1f92e8b03'
down_revision = 'a96d0b74b1af'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notes',
        sa.Column('id',         sa.Integer(),      nullable=False),
        sa.Column('user_id',    sa.Integer(),      nullable=False),
        sa.Column('title',      sa.String(255),    nullable=False, server_default='Untitled Note'),
        sa.Column('content',    sa.Text(),         nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(),     nullable=True),
        sa.Column('updated_at', sa.DateTime(),     nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notes_user_id'), 'notes', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_notes_user_id'), table_name='notes')
    op.drop_table('notes')
