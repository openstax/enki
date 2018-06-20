"""Commandline utility for publishing content"""
import click

from nebu import __version__
from ..config import prepare

from .atom import config_atom
from .get import get
from .environment import list_environments
from .publish import publish
from .validate import validate


__all__ = ('cli',)


def _version_callback(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    working_version = __version__
    click.echo('Nebuchadnezzar {}'.format(working_version))
    ctx.exit()


@click.group()
@click.option('--version', callback=_version_callback, is_flag=True,
              expose_value=False, is_eager=True,
              help='Show the version and exit')
@click.pass_context
def cli(ctx):
    env = prepare()
    ctx.obj = env


cli.add_command(config_atom)
cli.add_command(get)
cli.add_command(list_environments)
cli.add_command(publish)
cli.add_command(validate)
