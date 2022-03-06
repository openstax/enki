"""update indexes after renaming events table to jobs

Revision ID: 87653800ea49
Revises: 922575e7379e
Create Date: 2019-12-16 21:32:21.273190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '87653800ea49'
down_revision = '922575e7379e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('ix_jobs_collection_id'), 'jobs', ['collection_id'], unique=False)
    op.create_index(op.f('ix_jobs_created_at'), 'jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    op.drop_index('ix_events_collection_id', table_name='jobs')
    op.drop_index('ix_events_created_at', table_name='jobs')
    op.drop_index('ix_events_id', table_name='jobs')


def downgrade():
    op.create_index('ix_events_id', 'jobs', ['id'], unique=False)
    op.create_index('ix_events_created_at', 'jobs', ['created_at'], unique=False)
    op.create_index('ix_events_collection_id', 'jobs', ['collection_id'], unique=False)
    op.drop_index(op.f('ix_jobs_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_created_at'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_collection_id'), table_name='jobs')
