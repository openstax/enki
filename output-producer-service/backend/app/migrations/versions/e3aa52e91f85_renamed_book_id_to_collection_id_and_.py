"""renamed book_id to collection_id and added pdf_url field

Revision ID: e3aa52e91f85
Revises: 55eae8bd7f1e
Create Date: 2019-10-17 17:43:51.808721

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3aa52e91f85'
down_revision = '55eae8bd7f1e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('events', 'book_id', new_column_name='collection_id')
    op.add_column('events', sa.Column('pdf_url', sa.String(), nullable=True))


def downgrade():
    op.alter_column('collection_id', 'book_id')
    op.drop_column('events', 'pdf_url')
