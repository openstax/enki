import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import os
import imghdr

import click
import requests
from litezip import (
    convert_completezip,
)

from ..logger import logger
from ._common import common_params, confirm, get_base_url
from .exceptions import *  # noqa: F403


@click.command()
@common_params
@click.option('-d', '--output-dir', type=click.Path(),
              help="output directory name (can't previously exist)")
@click.argument('env')
@click.argument('col_id')
@click.argument('col_version')
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
        'archive{}{}'.format(sep, parsed_url.netloc),
    ] + list(parsed_url[2:])
    base_url = urlunparse(url_parts)

    col_hash = '{}/{}'.format(col_id, col_version)
    # Fetch metadata
    url = '{}/content/{}'.format(base_url, col_hash)
    resp = requests.get(url)
    if resp.status_code >= 400:
        raise MissingContent(col_id, col_version)
    col_metadata = resp.json()
    uuid = col_metadata['id']
    version = col_metadata['version']

    # Fetch extras (includes head and downloadable file info)
    url = '{}/extras/{}@{}'.format(base_url, uuid, version)
    resp = requests.get(url)

    if col_version == 'latest':
        version = resp.json()['headVersion']
        url = '{}/extras/{}@{}'.format(base_url, uuid, version)
        resp = requests.get(url)

    col_extras = resp.json()

    if version != col_extras['headVersion']:
        logger.warning("Fetching non-head version of {}."
                       "\n    Head: {},"
                       " requested {}".format(col_id,
                                              col_extras['headVersion'],
                                              version))
        if not(confirm("Fetch anyway? [y/n] ")):
            raise OldContent()

    # Get zip url from downloads
    zipinfo = [d for d in col_extras['downloads']
               if d['format'] == 'Offline ZIP'][0]

    if zipinfo['state'] != 'good':
        logger.info("The content exists,"
                    " but the completezip is {}".format(zipinfo['state']))
        raise MissingContent(col_id, col_version)

    url = '{}{}'.format(base_url, zipinfo['path'])

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
        "Removing resource files in {}".format(extracted_dir))
    for dirpath, dirnames, filenames in os.walk(str(extracted_dir)):
        for name in filenames:
            full_path = os.path.join(dirpath, name)
            if imghdr.what(full_path):
                os.remove(full_path)

    logger.debug(
        "Cleaning up extraction data at '{}'".format(tmp_dir))
    shutil.copytree(str(extracted_dir), str(output_dir))
    shutil.rmtree(str(tmp_dir))
