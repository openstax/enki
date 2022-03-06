import click

from app.db.schema import ContentServers
from app.db.session import db_session


@click.group()
def cli():
    pass


@click.command()
@click.confirmation_option(
    prompt='This will erase everything in the database. Do you want to continue?')
def reset_db():
    """Resets the database to the original state using alembic downgrade and upgrade commands"""
    from alembic.command import downgrade, upgrade
    from alembic.config import Config as AlembicConfig
    config = AlembicConfig('alembic.ini')
    downgrade(config, 'base')
    upgrade(config, 'head')
    click.echo('Database has been reset')


@click.command()
@click.option('-h', '--hostname', required=True, type=str)
@click.option('-n', '--name', required=True, type=str)
@click.option('-u', '--host_url', required=True, type=str)
def add_content_server(hostname, name, host_url):
    """Add a new content server to the database"""

    content_server = ContentServers(hostname=hostname,
                                    name=name,
                                    host_url=host_url)
    db_session.add(content_server)
    db_session.commit()

    click.echo(f'Content server added\n'
               f'hostname: {hostname}\nname:{name}\nurl:{host_url}')


cli.add_command(reset_db)
cli.add_command(add_content_server)

if __name__ == '__main__':
    cli()
