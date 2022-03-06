"""added version to Events table

Revision ID: 6f6dabc714c3
Revises: 2837298015bf
Create Date: 2019-11-04 14:24:03.502259

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f6dabc714c3'
down_revision = '2837298015bf'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('ix_content_servers_created_at'), 'content_servers', ['created_at'], unique=False)
    op.add_column('events', sa.Column('version', sa.String(), nullable=True))


def downgrade():
    op.drop_column('events', 'version')
    op.drop_index(op.f('ix_content_servers_created_at'), table_name='content_servers')
