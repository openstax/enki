"""add new column worker_version to jobs

Revision ID: 06691cbbbcea
Revises: 67cf464365a7
Create Date: 2020-12-17 20:57:17.864016

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '06691cbbbcea'
down_revision = '67cf464365a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('jobs', sa.Column('worker_version', sa.String(), nullable=True))


def downgrade():
    op.drop_column('jobs', 'worker_version')
