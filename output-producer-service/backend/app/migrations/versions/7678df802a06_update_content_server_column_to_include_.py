"""Update content server column to include simple name for the server

Revision ID: 7678df802a06
Revises: 6f6dabc714c3
Create Date: 2019-11-05 14:13:36.273407

"""
from alembic import op
from sqlalchemy.sql import select
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7678df802a06'
down_revision = '6f6dabc714c3'
branch_labels = None
depends_on = None

content_servers_table = sa.table('content_servers',
                                 sa.column('id', sa.Integer),
                                 sa.column('name', sa.String),
                                 sa.column('hostname', sa.String),
                                 sa.column('host_url', sa.String),
                                 sa.column('created_at', sa.DateTime),
                                 sa.column('updated_at', sa.DateTime)
                                 )


def upgrade():
    bind = op.get_bind()

    op.add_column('content_servers', sa.Column('name', sa.String()))

    s = select([content_servers_table])

    content_servers = bind.execute(s)

    for server in content_servers:
        simple_name = server['hostname'].split('.')[0]
        update = content_servers_table.update().where(
            content_servers_table.c.id == server["id"]).values(name=simple_name)

        bind.execute(update)


def downgrade():
    op.drop_column('content_servers', 'name')
