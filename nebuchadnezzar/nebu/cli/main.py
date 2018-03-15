# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import click
import requests
from litezip import (
    Collection,
    convert_completezip,
    parse_litezip,
    validate_litezip,
)

from ..logger import configure_logging, logger


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
        message = "output directory cannot exist:  {}".format(output_dir)
        super(ExistingOutputDir, self).__init__(message)


class MissingContent(click.ClickException):
    exit_code = 4

    def __init__(self, id, version):
        message = "content unavailable for '{}/{}'".format(id, version)
        super(MissingContent, self).__init__(message)


def set_verbosity(verbose):
    config = console_logging_config.copy()
    if verbose:
        level = 'DEBUG'
    else:
        level = 'INFO'
    config['loggers']['nebuchadnezzar']['level'] = level
    configure_logging(config)


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='enable verbosity')
def cli(verbose):
    set_verbosity(verbose)


@cli.command()
@click.option('-d', '--output-dir', type=click.Path(),
              help="output directory name (can't previously exist)")
@click.argument('col_id')
@click.argument('col_version', default='latest')
def get(col_id, col_version, output_dir):
    """download and expand the completezip to the current working directory"""
    # FIXME We need to be able to build urls to multiple services.
    #       For now we'll use an environment variable
    scheme = os.environ.get('XXX_SCHEME', 'https')
    host = os.environ.get('XXX_HOST', 'cnx.org')
    sep = len(host.split('.')) > 2 and '-' or '.'
    url = '{}://legacy{}{}/content/{}/{}/complete'.format(
        scheme, sep, host, col_id, col_version)
    # / FIXME

    tmp_dir = Path(tempfile.mkdtemp())
    zip_filepath = tmp_dir / 'complete.zip'
    if output_dir is None:
        output_dir = Path.cwd() / col_id
    else:
        output_dir = Path(output_dir)

    if output_dir.exists():
        raise ExistingOutputDir(output_dir)

    logger.debug('Request sent to {} ...'.format(url))
    resp = requests.get(url, stream=True)

    if not resp:
        logger.debug("Response code is {}".format(resp.status_code))
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


def _publish(struct, message):
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
    # FIXME We need to be able to build urls to multiple services.
    #       For now we'll use an environment variable
    scheme = os.environ.get('XXX_SCHEME', 'https')
    host = os.environ.get('XXX_HOST', 'cnx.org')
    url = '{}://{}/api/v3/publish'.format(scheme, host)
    # FIXME We don't have nor want explicit setting of the publisher.
    #       The publisher will come through as part of the authentication
    #       information, which will be in a later implementation.
    #       For now, pull it out of a environment variable.
    data = {
        'publisher': os.environ.get('XXX_PUBLISHER', 'OpenStaxCollege'),
        'message': message,
    }
    files = {
        'file': ('contents.zip', zip_file.open('rb'),),
    }
    resp = requests.post(url, data=data, files=files)

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
@click.argument('content_dir',
                type=click.Path(exists=True, file_okay=False))
@click.argument('publication_message', type=str)
def publish(content_dir, publication_message):
    content_dir = Path(content_dir).resolve()
    struct = parse_litezip(content_dir)

    if is_valid(struct):
        has_published = _publish(struct, publication_message)
        if has_published:
            logger.info("Great work!!! =D")
        else:
            logger.info("Stop the Press!!! =()")
            sys.exit(1)
    else:
        logger.info("We've got problems... :(")
        sys.exit(1)
