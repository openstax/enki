"""add column error_message to jobs

Revision ID: 7744a6c02085
Revises: b1a7843ab462
Create Date: 2021-01-05 15:48:56.095121

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7744a6c02085'
down_revision = 'b1a7843ab462'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('jobs', sa.Column('error_message', sa.String(), nullable=True))


def downgrade():
    op.drop_column('jobs', 'error_message')
