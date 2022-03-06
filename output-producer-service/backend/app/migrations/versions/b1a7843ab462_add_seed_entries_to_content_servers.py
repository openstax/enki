"""add seed entries to content_servers

Revision ID: b1a7843ab462
Revises: 06691cbbbcea
Create Date: 2020-12-22 19:11:43.657348

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1a7843ab462'
down_revision = '06691cbbbcea'
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
    utcnow = datetime.utcnow()
    server_data = [{'name': 'production', 'hostname': 'cnx.org', 'host_url': 'https://cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'name': 'content06', 'hostname': 'content06.cnx.org', 'host_url': 'https://content06.cnx.org', 'created_at': utcnow, 'updated_at': utcnow}]
    insert = content_servers_table.insert().values(server_data)
    bind.execute(insert)


def downgrade():
    bind = op.get_bind()
    delete_seed = content_servers_table.delete().where(content_servers_table.c.name.in_(['production','content06']))
    bind.execute(delete_seed)