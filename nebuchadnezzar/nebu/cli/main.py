# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import shutil
import tempfile
import zipfile
from pathlib import Path

import click
import requests
from litezip import convert_completezip, parse_litezip, validate_litezip

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
    url = 'http://legacy.cnx.org/content/{}/{}/complete'.format(
        col_id, col_version)

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


@cli.command()
@click.argument('content_dir', default='.',
                type=click.Path(exists=True, file_okay=False))
def validate(content_dir):
    content_dir = Path(content_dir).resolve()
    struct = parse_litezip(content_dir)

    has_errors = False
    cwd = Path('.').resolve()
    for filepath, error_msg in validate_litezip(struct):
        has_errors = True
        filepath = filepath.relative_to(cwd)
        logger.error('{}:{}'.format(filepath, error_msg))

    if has_errors:
        logger.info("We've got problems... :(")
    else:
        logger.info("All good! :)")
