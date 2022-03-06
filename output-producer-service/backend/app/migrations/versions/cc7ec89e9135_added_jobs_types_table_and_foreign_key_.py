"""Added jobs types table and foreign key row to jobs

Revision ID: cc7ec89e9135
Revises: 59dbc5b20d2e
Create Date: 2020-09-08 14:39:19.852731

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cc7ec89e9135'
down_revision = '59dbc5b20d2e'
branch_labels = None
depends_on = None

job_types_table = sa.table('job_types',
                        sa.column('id', sa.Integer),
                        sa.column('name', sa.String),
                        sa.column('created_at', sa.DateTime),
                        sa.column('updated_at', sa.DateTime)
                        )

def upgrade():
    op.create_table('job_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_types_id'), 'job_types', ['id'], unique=False)
    op.add_column('jobs', sa.Column('job_type_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'jobs', 'job_types', ['job_type_id'], ['id'])
    op.create_index(op.f('ix_jobs_job_type'), 'jobs', ['job_type_id'], unique=False)
    
    utcnow = datetime.utcnow()

    server_data = [{'id': 1, 'name': 'pdf', 'created_at': utcnow, 'updated_at': utcnow},
                   {'id': 2, 'name': 'distribution-preview', 'created_at': utcnow, 'updated_at': utcnow}]

    bind = op.get_bind()
    insert = job_types_table.insert().values(server_data)
    bind.execute(insert)

    op.execute("update jobs set job_type_id = 1")


def downgrade():
    op.drop_index(op.f('ix_jobs_job_type'), table_name='jobs')
    op.drop_constraint('jobs_job_type_id_fkey', 'jobs', type_='foreignkey')
    op.drop_column('jobs', 'job_type_id')
    op.drop_index(op.f('ix_job_types_id'), table_name='job_types')
    op.drop_table('job_types')
