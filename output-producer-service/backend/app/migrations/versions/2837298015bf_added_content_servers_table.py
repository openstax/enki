"""added content_servers table

Revision ID: 2837298015bf
Revises: e3aa52e91f85
Create Date: 2019-10-21 15:52:38.549364

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2837298015bf'
down_revision = 'e3aa52e91f85'
branch_labels = None
depends_on = None

content_servers_table = sa.table('content_servers',
                        sa.column('id', sa.Integer),
                        sa.column('hostname', sa.String),
                        sa.column('host_url', sa.String),
                        sa.column('created_at', sa.DateTime),
                        sa.column('updated_at', sa.DateTime)
                        )


def upgrade():
    bind = op.get_bind()

    op.create_table('content_servers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hostname', sa.String(), nullable=True),
    sa.Column('host_url', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_servers_id'), 'content_servers', ['id'], unique=False)
    op.add_column('events', sa.Column('content_server_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_events_collection_id'), 'events', ['collection_id'], unique=False)
    op.drop_index('ix_events_book_id', table_name='events')
    op.create_foreign_key(None, 'events', 'content_servers', ['content_server_id'], ['id'])

    utcnow = datetime.utcnow()

    server_data = [{'hostname': 'content01.cnx.org', 'host_url': 'https://content01.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'content02.cnx.org', 'host_url': 'https://content02.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'content03.cnx.org', 'host_url': 'https://content03.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'content04.cnx.org', 'host_url': 'https://content04.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'content05.cnx.org', 'host_url': 'https://content05.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'dev.cnx.org', 'host_url': 'https://dev.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'qa.cnx.org', 'host_url': 'https://qa.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'staging.cnx.org', 'host_url': 'https://staging.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'easyvm5.cnx.org', 'host_url': 'https://easyvm5.cnx.org', 'created_at': utcnow, 'updated_at': utcnow},
                   {'hostname': 'katalyst01.cnx.org', 'host_url': 'https://katalyst01.cnx.org', 'created_at': utcnow, 'updated_at': utcnow}]

    insert = content_servers_table.insert().values(server_data)

    bind.execute(insert)


def downgrade():
    op.drop_constraint('events_content_server_id_fkey', 'events', type_='foreignkey')
    op.create_index('ix_events_book_id', 'events', ['collection_id'], unique=False)
    op.drop_index(op.f('ix_events_collection_id'), table_name='events')
    op.drop_column('events', 'content_server_id')
    op.drop_index(op.f('ix_content_servers_id'), table_name='content_servers')
    op.drop_table('content_servers')
