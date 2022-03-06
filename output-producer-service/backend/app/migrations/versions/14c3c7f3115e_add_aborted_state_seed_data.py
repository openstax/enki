"""add aborted state seed data

Revision ID: 14c3c7f3115e
Revises: 7744a6c02085
Create Date: 2021-01-13 23:14:38.997558

"""
from alembic import op
import sqlalchemy as sa

from datetime import datetime


# revision identifiers, used by Alembic.
revision = '14c3c7f3115e'
down_revision = '7744a6c02085'
branch_labels = None
depends_on = None


status_table = sa.table('status',
                        sa.column('id', sa.Integer),
                        sa.column('name', sa.String),
                        sa.column('created_at', sa.DateTime),
                        sa.column('updated_at', sa.DateTime)
                        )


def upgrade():
    utcnow = datetime.utcnow()
    bind = op.get_bind()

    status_data = [{'id': 6, 'name': 'aborted', 'created_at': utcnow, 'updated_at': utcnow}]

    insert = status_table.insert().values(status_data)

    bind.execute(insert)


def downgrade():
    bind = op.get_bind()
    delete_seed = status_table.delete().where(status_table.c.id == op.inline_literal(6) )
    bind.execute(delete_seed)
