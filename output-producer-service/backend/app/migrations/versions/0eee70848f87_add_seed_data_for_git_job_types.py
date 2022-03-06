"""add seed data for git job types

Revision ID: 0eee70848f87
Revises: cc7ec89e9135
Create Date: 2020-11-05 20:34:27.770606

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

from app.data_models.models import JobType


# revision identifiers, used by Alembic.
revision = '0eee70848f87'
down_revision = 'cc7ec89e9135'
branch_labels = None
depends_on = None

job_types_table = sa.table('job_types',
                        sa.column('id', sa.Integer),
                        sa.column('name', sa.String),
                        sa.column('created_at', sa.DateTime),
                        sa.column('updated_at', sa.DateTime)
                        )

jobs_table = sa.table('jobs', sa.column('job_type_id'))

def upgrade():
    utcnow = datetime.utcnow()
    server_data = [{'id': 3, 'name': 'git-pdf', 'created_at': utcnow, 'updated_at': utcnow},
                   {'id': 4, 'name': 'git-distribution-preview', 'created_at': utcnow, 'updated_at': utcnow}]

    bind = op.get_bind()
    insert = job_types_table.insert().values(server_data)
    bind.execute(insert)


def downgrade():
    bind = op.get_bind()
    delete_jobs_of_seeded_type = jobs_table.delete().where(jobs_table.c.job_type_id.in_([3,4]))
    delete_seed = job_types_table.delete().where(job_types_table.c.id.in_([3,4]))
    bind.execute(delete_jobs_of_seeded_type)
    bind.execute(delete_seed)
