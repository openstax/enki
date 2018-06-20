import os
import sys
import tempfile
import zipfile
from pathlib import Path

import click
import requests
from litezip import (
    parse_litezip,
    Collection,
)

from ._common import common_params, get_base_url, logger
from .validate import is_valid


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


@click.command()
@common_params
@click.argument('env')
@click.argument('content_dir',
                type=click.Path(exists=True, file_okay=False))
@click.argument('publication_message', type=str)
@click.option('--skip-validation', is_flag=True)
@click.pass_context
def publish(ctx, env, content_dir, publication_message, skip_validation):
    base_url = get_base_url(ctx, env)

    content_dir = Path(content_dir).resolve()
    struct = parse_litezip(content_dir)

    if not skip_validation and not is_valid(struct):
        logger.info("We've got problems... :(")
        sys.exit(1)

    has_published = _publish(base_url, struct, publication_message)
    if has_published:
        logger.info("Great work!!! =D")
    else:
        logger.info("Stop the Press!!! =()")
        sys.exit(1)
