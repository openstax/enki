"""make content_server fields not nullable

Revision ID: 59dbc5b20d2e
Revises: 6b83ef5cce00
Create Date: 2020-01-17 23:00:54.736531

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59dbc5b20d2e'
down_revision = '6b83ef5cce00'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('content_servers', 'host_url',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('content_servers', 'hostname',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('content_servers', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)


def downgrade():
    op.alter_column('content_servers', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('content_servers', 'hostname',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('content_servers', 'host_url',
               existing_type=sa.VARCHAR(),
               nullable=True)
