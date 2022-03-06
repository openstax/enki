"""Add display_name to job types

Revision ID: 67cf464365a7
Revises: 0eee70848f87
Create Date: 2020-12-09 16:26:12.185099

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67cf464365a7'
down_revision = '0eee70848f87'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job_types', sa.Column('display_name', sa.String(), nullable=True))

    job_types_table = sa.table('job_types',
                        sa.column('id', sa.Integer),
                        sa.column('name', sa.String),
                        sa.column('display_name', sa.String),
                        sa.column('created_at', sa.DateTime),
                        sa.column('updated_at', sa.DateTime)
                        )
    data = {
        1: 'PDF',
        2: 'Web Preview',
        3: 'PDF (git)',
        4: 'Web Preview (git)'
    }

    bind = op.get_bind()
    for item_id, display_name in data.items():
        update = job_types_table \
            .update() \
            .where(job_types_table.c.id==op.inline_literal(item_id)) \
            .values({'display_name': op.inline_literal(display_name)})
        bind.execute(update)

    op.alter_column('job_types', 'display_name', nullable=False)

def downgrade():
    op.drop_column('job_types', 'display_name')
