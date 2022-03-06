"""rename Events table to Jobs

Revision ID: 922575e7379e
Revises: 7678df802a06
Create Date: 2019-12-13 04:14:23.483457

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '922575e7379e'
down_revision = '7678df802a06'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("events", "jobs")


def downgrade():
    op.rename_table("jobs", "events")
