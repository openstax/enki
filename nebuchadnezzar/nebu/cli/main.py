# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import click
import requests
import pkg_resources
from litezip import (
    Collection,
    convert_completezip,
    parse_litezip,
    validate_litezip,
)

from nebu import __version__
from ..logger import configure_logging, logger
from ..config import prepare


__all__ = ('cli',)


console_logging_config = {
    'version': 1,
    'formatters': {
        'cli': {
            'format': '%(message)s',
        },
    },
    'filters': {},
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'cli',
            'filters': [],
            'stream': 'ext://sys.stderr',
        },
    },
    'loggers': {
        'nebuchadnezzar': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': 0,
        },
        'litezip': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': 0,
        },
    },
    'root': {
        'level': 'NOTSET',
        'handlers': [],
    },
}


class ExistingOutputDir(click.ClickException):
    exit_code = 3

    def __init__(self, output_dir):
        message = "directory already exists:  {}".format(output_dir)
        super(ExistingOutputDir, self).__init__(message)


class MissingContent(click.ClickException):
    exit_code = 4

    def __init__(self, id, version):
        message = "content unavailable for '{}/{}'".format(id, version)
        super(MissingContent, self).__init__(message)


class UnknownEnvironment(click.ClickException):
    exit_code = 5

    def __init__(self, environ_name):
        message = "unknown environment '{}'".format(environ_name)
        super(UnknownEnvironment, self).__init__(message)


def set_verbosity(verbose):
    config = console_logging_config.copy()
    if verbose:
        level = 'DEBUG'
    else:
        level = 'INFO'
    config['loggers']['nebuchadnezzar']['level'] = level
    configure_logging(config)


def get_base_url(context, environ_name):
    try:
        return context.obj['settings']['environs'][environ_name]['url']
    except KeyError:
        raise UnknownEnvironment(environ_name)


def _version_callback(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    working_version = __version__
    click.echo('Nebuchadnezzar {}'.format(working_version))
    ctx.exit()


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='enable verbosity')
@click.option('--version', callback=_version_callback, is_flag=True,
              expose_value=False, is_eager=True,
              help='Show the version and exit')
@click.pass_context
def cli(ctx, verbose):
    env = prepare()
    ctx.obj = env
    set_verbosity(verbose)
    logger.debug('Using the configuration file at {}'
                 .format(env['settings']['_config_file']))


@cli.command()
@click.option('-d', '--output-dir', type=click.Path(),
              help="output directory name (can't previously exist)")
@click.argument('env')
@click.argument('col_id')
@click.argument('col_version', default='latest')
@click.pass_context
def get(ctx, env, col_id, col_version, output_dir):
    """download and expand the completezip to the current working directory"""
    # Determine the output directory
    tmp_dir = Path(tempfile.mkdtemp())
    zip_filepath = tmp_dir / 'complete.zip'
    if output_dir is None:
        output_dir = Path.cwd() / col_id
    else:
        output_dir = Path(output_dir)

    if output_dir.exists():
        raise ExistingOutputDir(output_dir)

    # Build the base url
    base_url = get_base_url(ctx, env)
    parsed_url = urlparse(base_url)
    sep = len(parsed_url.netloc.split('.')) > 2 and '-' or '.'
    url_parts = [
        parsed_url.scheme,
        'legacy{}{}'.format(sep, parsed_url.netloc),
    ] + list(parsed_url[2:])
    base_url = urlunparse(url_parts)

    if col_version == 'latest':
        # See https://github.com/Connexions/nebuchadnezzar/issues/44
        # Acquire the specific version of the completezip
        logger.debug("Requesting a specific version for {}".format(col_id))
        url = '{}/content/{}/latest/getVersion'.format(base_url, col_id)
        resp = requests.get(url)
        if resp.status_code >= 400:
            raise MissingContent(col_id, col_version)
        col_version = resp.text.strip()

    # Build the url to the completezip
    url = '{}/content/{}/{}/complete'.format(base_url, col_id, col_version)

    logger.debug('Request sent to {} ...'.format(url))
    resp = requests.get(url, stream=True)

    if not resp:
        logger.debug("Response code is {}".format(resp.status_code))
        raise MissingContent(col_id, col_version)
    elif resp.status_code == 204:
        logger.info("The content exists, but the completezip is missing")
        raise MissingContent(col_id, col_version)

    content_size = int(resp.headers['Content-Length'].strip())
    label = 'Downloading {}'.format(col_id)
    progressbar = click.progressbar(label=label, length=content_size)
    with progressbar as pbar, zip_filepath.open('wb') as fb:
        for buffer_ in resp.iter_content(1024):
            if buffer_:
                fb.write(buffer_)
                pbar.update(len(buffer_))

    label = 'Extracting {}'.format(col_id)
    with zipfile.ZipFile(str(zip_filepath), 'r') as zip:
        progressbar = click.progressbar(iterable=zip.infolist(),
                                        label=label,
                                        show_eta=False)
        with progressbar as pbar:
            for i in pbar:
                zip.extract(i, path=str(tmp_dir))

    extracted_dir = Path([x for x in tmp_dir.glob('col*_complete')][0])

    logger.debug(
        "Converting completezip at '{}' to litezip".format(extracted_dir))
    convert_completezip(extracted_dir)

    logger.debug(
        "Cleaning up extraction data at '{}'".format(tmp_dir))
    shutil.copytree(str(extracted_dir), str(output_dir))
    shutil.rmtree(str(tmp_dir))


def is_valid(struct):
    """Checks validity of a litezip's contents with commandline ouput
    containing any validation errors.
    Returns True when the content is value and False if not.

    """

    has_errors = False
    cwd = Path('.').resolve()
    for filepath, error_msg in validate_litezip(struct):
        has_errors = True
        filepath = filepath.relative_to(cwd)
        logger.error('{}:{}'.format(filepath, error_msg))
    return not has_errors


@cli.command()
@click.argument('content_dir', default='.',
                type=click.Path(exists=True, file_okay=False))
def validate(content_dir):
    content_dir = Path(content_dir).resolve()
    struct = parse_litezip(content_dir)

    if is_valid(struct):
        logger.info("All good! :)")
    else:
        logger.info("We've got problems... :(")


@cli.command(name='list')
@click.pass_context
def environments(context):
    """List of valid environment names from config.

    Names are required for get and publish"""
    envs = context.obj['settings']['environs']
    lines = []
    for env, val in envs.items():
        lines.append('{}\t {url}'.format(env, **val))
    lines.sort()
    logger.info('\n'.join(lines))


def _publish(base_url, struct, message):
    """Publish the struct to a repository"""
    collection_id = struct[0].id
    # Base encapsulating directory within the zipfile
    base_file_path = Path(collection_id)

    # Zip it up!
    # TODO Move this block of logic to litezip. Maybe?
    _, zip_file = tempfile.mkstemp()
    zip_file = Path(zip_file)
    with zipfile.ZipFile(str(zip_file), 'w') as zb:
        for model in struct:
            # Write the content file into the zip.
            if isinstance(model, Collection):
                file = model.file
                rel_file_path = base_file_path / model.file.name
            else:  # Module
                file = model.file
                rel_file_path = base_file_path / model.id / model.file.name
            zb.write(str(file), str(rel_file_path))
            # TODO Include resource files

    # Send it!
    url = '{}/api/publish-litezip'.format(base_url)
    # FIXME We don't have nor want explicit setting of the publisher.
    #       The publisher will come through as part of the authentication
    #       information, which will be in a later implementation.
    #       For now, pull it out of a environment variable.
    headers = {'X-API-Version': '3'}
    data = {
        'publisher': os.environ.get('XXX_PUBLISHER', 'OpenStaxCollege'),
        'message': message,
    }
    files = {
        'file': ('contents.zip', zip_file.open('rb'),),
    }
    resp = requests.post(url, data=data, files=files, headers=headers)

    # Clean up!
    zip_file.unlink()

    # Process any response messages
    if resp.status_code == 200:
        # TODO Nicely format this stuff. Wait for the Bravado client
        #      implementation to work with models to make this work easier.
        logger.debug('Temporary raw output...')
        from pprint import pformat
        logger.info('Publishing response: \n{}'
                    .format(pformat(resp.json())))
    elif resp.status_code == 400:
        # This way be Errors
        # TODO Nicely format this stuff. Wait for the Bravado client
        #      implementation to work with models to make this work easier.
        logger.debug('Temporary raw output...')
        logger.error('ERROR: \n{}'.format(resp.content))
        return False
    else:  # pragma: no cover
        logger.error("unknown response:\n  status: {}\n  contents: {}"
                     .format(resp.status_code, resp.text))
        raise RuntimeError('unknown response, see output above')

    return True


@cli.command()
@click.argument('env')
@click.argument('content_dir',
                type=click.Path(exists=True, file_okay=False))
@click.argument('publication_message', type=str)
@click.pass_context
def publish(ctx, env, content_dir, publication_message):
    base_url = get_base_url(ctx, env)

    content_dir = Path(content_dir).resolve()
    struct = parse_litezip(content_dir)

    if is_valid(struct):
        has_published = _publish(base_url, struct, publication_message)
        if has_published:
            logger.info("Great work!!! =D")
        else:
            logger.info("Stop the Press!!! =()")
            sys.exit(1)
    else:
        logger.info("We've got problems... :(")
        sys.exit(1)


_confirmation_prompt = (
    'A backup of your atom-config will be created.\n'
    'However, this will overwrite your config... continue?'
)
_ATOM_CONFIG_TEMPLATE = """\
"*":
  core:
    customFileTypes:

      # Add this to the bottom of the customFileTypes area.
      # Note: Indentation is important!
      "text.xml": [
        "index.cnxml"
      ]


  # And then this to the bottom of the file
  # 1. Make sure "linter-autocomplete-jing" only occurs once in this file!
  # 1. make sure it is indented by 2 spaces just like it is in this example.

  "linter-autocomplete-jing":
    displaySchemaWarnings: true
    rules: [
      {
        priority: 1
        test:
          pathRegex: ".cnxml$"
        outcome:
          schemaProps: [
            {
              lang: "rng"
              path: "%s"
            }
          ]
      }
    ]
"""


@cli.command(name='config-atom')
@click.confirmation_option(prompt=_confirmation_prompt)
def config_atom():
    filepath = Path.home() / '.atom/config.cson'
    if not filepath.parent.exists():
        filepath.parent.mkdir()
    if filepath.exists():
        backup_filepath = filepath.parent / 'config.cson.bak'
        filepath.rename(backup_filepath)
        logger.info("Wrote backup to {}".format(backup_filepath.resolve()))

    cnxml_jing_rng = pkg_resources.resource_filename(
        'cnxml',  # find by package name
        'xml/cnxml/schema/rng/0.7/cnxml-jing.rng')
    with filepath.open('w') as fb:
        fb.write(_ATOM_CONFIG_TEMPLATE % cnxml_jing_rng)

    logger.info("Wrote {}".format(filepath.resolve()))
