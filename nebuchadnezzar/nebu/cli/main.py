"""Commandline utility for publishing content"""
import click
import pkg_resources
import sys
import requests
import re
from collections import defaultdict

from nebu import __version__
from ..config import prepare

from .assemble import assemble
from .atom import config_atom
from .get import head, get
from .environment import list_environments
from .ping import ping
from .publish import publish
from .validate import validate


__all__ = ('cli',)


def extract_sub_dict(dict, path):
    """Get values from a given path of keys"""
    for item in path:
        dict = dict[item]
    return dict


def get_remote_releases(json_url, json_path):
    """Get list of releases from remote json file, sorted from oldest
    to newest. If a network error occurs, returns an empty list.
    """
    try:
        json = requests.get(json_url).json()
    except requests.exceptions.RequestException:
        click.echo("Could not connect to find new releases.",
                   file=sys.stderr)
        return []
    try:
        releases_from_request = extract_sub_dict(json, json_path)
    except KeyError:
        click.echo("The remote JSON schema seems to have changed.\n"
                   "Please submit a bug report.",
                   file=sys.stderr)
        return []
    sorted_releases = sorted(list(releases_from_request.keys()))
    return sorted_releases


def get_pypi_releases():
    """Fetch Neb package releases available via pip"""
    url = "https://pypi.org/pypi/nebuchadnezzar/json"
    path = ["releases"]
    return get_remote_releases(url, path)


def get_latest_released_version(release_source_function):
    """Get the latest released version of Neb. If no releases found,
    returns an empty string
    """
    try:
        return release_source_function()[-1]
    except IndexError:
        return ""


def _version_callback(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    working_version = __version__
    click.echo('Nebuchadnezzar {}'.format(working_version))
    installed_semver_match = re.match(r"^\d+(\.\d+)*(?=\+|$)",
                                      working_version)
    try:
        installed_semver = installed_semver_match.group(0)
    except AttributeError:
        click.echo("The semantic version of Neb could not be read.\n"
                   "Please submit a bug report.",
                   file=sys.stderr)
        ctx.exit()
    latest_version = get_latest_released_version(get_pypi_releases)
    if installed_semver < latest_version:
        click.echo("Version {0} available for install.".format(latest_version),
                   file=sys.stderr)
    ctx.exit()


class HelpSectionsGroup(click.Group):
    def __init__(self, *args, **kwargs):
        self.help_sections = {}
        super().__init__(*args, **kwargs)

    def format_get_commands(self, ctx):
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue  # pragma: no cover
            if cmd.hidden:
                continue  # pragma: no cover

            commands.append((subcommand, cmd))
        return commands

    def format_commands(self, ctx, formatter):
        commands = self.format_get_commands(ctx)
        if len(commands) == 0:
            return

        limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)
        section_rows = defaultdict(list)
        for subcommand, cmd in commands:
            help = cmd.get_short_help_str(limit)
            row = section_rows[self.help_sections.get(subcommand, 'Other')]
            row.append((subcommand, help))

        with formatter.section('Commands'):
            for section_name, rows in sorted(section_rows.items()):
                formatter.write_text('[{}]'.format(section_name))
                formatter.write_dl(rows)
                formatter.write_text('')

    def add_command(self, cmd, name=None, help_section='Other'):
        super().add_command(cmd, name)
        name = name or cmd.name
        self.help_sections[name] = help_section

    def command(self, *args, **kwargs):
        help_section = kwargs.pop('help_section', 'Other')
        group = super()

        def decorator(f):
            cmd = group.command(*args, **kwargs)(f)
            self.help_sections[cmd.name] = help_section
            return cmd
        return decorator


@click.group(cls=HelpSectionsGroup)
@click.option('--version', callback=_version_callback, is_flag=True,
              expose_value=False, is_eager=True,
              help='Show the version and exit')
@click.pass_context
def cli(ctx):
    env = prepare()
    ctx.obj = env


cli.add_command(assemble, help_section='Stock')
cli.add_command(config_atom, help_section='Stock')
cli.add_command(get, help_section='Stock')
cli.add_command(head, help_section='Stock')
cli.add_command(list_environments, help_section='Stock')
cli.add_command(ping, help_section='Stock')
cli.add_command(publish, help_section='Stock')
cli.add_command(validate, help_section='Stock')

for entry_point in pkg_resources.iter_entry_points('neb.extension'):
    entry_point.load()(cli)  # pragma: no cover
