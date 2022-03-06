"""update job types to use web hosting

Revision ID: c242e42f4bc1
Revises: 14c3c7f3115e
Create Date: 2021-02-26 21:45:55.546275

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c242e42f4bc1'
down_revision = '14c3c7f3115e'
branch_labels = None
depends_on = None

job_types_table = sa.table('job_types',
                           sa.column('id', sa.Integer),
                           sa.column('name', sa.String),
                           sa.column('created_at', sa.DateTime),
                           sa.column('updated_at', sa.DateTime)
                           )


def upgrade():
    bind = op.get_bind()
    stmt = sa.sql.select([job_types_table]).where(
        job_types_table.c.id.in_([2, 4])
    )
    dist_results = bind.execute(stmt)

    for result in dist_results:
        original_name = result["name"]
        new_name = original_name.replace("distribution", "web-hosting")

        update_stmt = job_types_table.update().values(name=new_name).where(
            job_types_table.c.id == result["id"])

        bind.execute(update_stmt)


def downgrade():
    bind = op.get_bind()

    stmt = sa.sql.select([job_types_table]).where(
        job_types_table.c.id.in_([2, 4])
    )
    web_hosting_results = bind.execute(stmt)

    for result in web_hosting_results:
        original_name = result["name"]
        new_name = original_name.replace("web-hosting", "distribution")

        update_stmt = job_types_table.update().values(name=new_name).where(
            job_types_table.c.id == result["id"])

        bind.execute(update_stmt)
