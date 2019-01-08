import os
import sys
import tempfile
import zipfile
from pathlib import Path

import click
import requests
from requests.auth import HTTPBasicAuth
from litezip import (
    parse_collection,
    parse_module,
    Collection,
)

from ._common import common_params, get_base_url, logger, calculate_sha1
from .validate import is_valid


def parse_book_tree(bookdir):
    """Converts filesystem booktree back to a struct"""
    struct = []
    ex = [lambda filepath: '.sha1sum' in filepath.name]
    for dirname, subdirs, filenames in os.walk(str(bookdir)):
        if 'collection.xml' in filenames:
            path = Path(dirname)
            sha1s = get_sha1s_dict(path)
            struct.append((parse_collection(path, excludes=ex), sha1s))
        elif 'index.cnxml' in filenames:
            path = Path(dirname)
            sha1s = get_sha1s_dict(path)
            struct.append((parse_module(path, excludes=ex), sha1s))

    return struct


def get_sha1s_dict(path):
    """Returns a dict of sha1-s by filename"""
    try:
        with (path / '.sha1sum').open('r') as sha_file:
            return {line.split('  ')[1].strip(): line.split('  ')[0].strip()
                    for line in sha_file if not line.startswith('#')}
    except FileNotFoundError:
        return {}


def filter_what_changed(contents):
    changed = []

    collection, coll_sha1s_dict = contents.pop(0)

    for model, sha1s_dict in contents:
        new_mod_resources = []
        for resource in model.resources:
            cached_sha1 = sha1s_dict.get(resource.filename.strip())

            if cached_sha1 is None or resource.sha1 != cached_sha1:
                new_mod_resources.append(resource)

        # if the model changed or any of its resources
        mod_cached_sha1 = sha1s_dict.get(model.file.name.strip())
        mod_actual_sha1 = calculate_sha1(model.file)
        if mod_actual_sha1 != mod_cached_sha1 or len(new_mod_resources) > 0:
            new_model = model._replace(resources=tuple(new_mod_resources))
            changed.append(new_model)

    """Now check the Collection and the Collection's resources"""
    new_col_resources = []
    for resource in collection.resources:
        cached_sha1 = coll_sha1s_dict.get(resource.filename.strip())

        if cached_sha1 is None or resource.sha1 != cached_sha1:
            new_col_resources.append(resource)

    coll_changed = False
    new_coll = collection._replace(resources=tuple(new_col_resources))
    if len(new_col_resources) > 0:
        changed.insert(0, new_coll)  # because `_publish` will expect this
        coll_changed = True

    # If any modules changed, assume collection changed
    cached_coll_sha1 = coll_sha1s_dict.get('collection.xml')
    if len(changed) > 0 or coll_sha1s_dict.get('collection.xml') is None or \
       cached_coll_sha1 != calculate_sha1(collection.file):
        if not coll_changed:  # coll already in changed.
            changed.insert(0, new_coll)
        return changed
    else:  # No changes at all
        return []


def gen_zip_file(base_file_path, struct):
    # TODO Move this block of logic to litezip. Maybe?
    _, zip_file = tempfile.mkstemp()
    zip_file = Path(zip_file)

    with zipfile.ZipFile(str(zip_file), 'w') as zb:
        for model in struct:
            files = []
            # Write the content file into the zip.
            if isinstance(model, Collection):
                file = model.file
                full_path = base_file_path / file.name
                files.append((file, full_path))

                for resource in model.resources:
                    full_path = base_file_path / resource.filename
                    files.append((resource.data, full_path))
            else:  # Module
                file = model.file
                full_path = base_file_path / model.id / file.name
                files.append((file, full_path))

                for resource in model.resources:
                    full_path = base_file_path / model.id / resource.filename
                    files.append((resource.data, full_path))

            for file, full_path in files:
                zb.write(str(file), str(full_path))

    return zip_file


def _publish(base_url, struct, message, username, password):
    if len(struct) == 0:
        logger.debug('Temporary raw output...')
        logger.error('Nothing changed, nothing to publish.\n')
        return False

    auth = HTTPBasicAuth(username, password)

    """Check for good credentials"""
    auth_ping_url = '{}/api/auth-ping'.format(base_url)
    auth_ping_resp = requests.get(auth_ping_url, auth=auth)

    if auth_ping_resp.status_code == 401:
        logger.debug('Temporary raw output...')
        logger.error('Bad credentials: \n{}'.format(auth_ping_resp.content))
        return False

    """Check for permission to publish"""
    publish_ping_url = '{}/api/publish-ping'.format(base_url)
    publish_ping_resp = requests.get(publish_ping_url, auth=auth)

    if publish_ping_resp.status_code == 401:
        logger.debug('Temporary raw output...')
        logger.error('Publishing not allowed: \n{}'.format(
            publish_ping_resp.content))
        return False

    """Publish the struct to a repository"""
    collection_id = struct[0].id
    # Base encapsulating directory within the zipfile
    base_file_path = Path(collection_id)

    # Zip it up!
    zip_file = gen_zip_file(base_file_path, struct)

    url = '{}/api/publish-litezip'.format(base_url)
    headers = {'X-API-Version': '3'}

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
    # Send it!
    resp = requests.post(url, data=data, files=files,
                         auth=auth, headers=headers)

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
@click.option('-m', '--message', type=str,
              prompt='Publication message')
@click.option('-u', '--username', type=str, prompt=True)
@click.option('-p', '--password', type=str, prompt=True, hide_input=True)
@click.option('--skip-validation', is_flag=True)
@click.pass_context
def publish(ctx, env, content_dir, message, username, password,
            skip_validation):
    base_url = get_base_url(ctx, env)

    content_dir = Path(content_dir).resolve()
    struct = parse_book_tree(content_dir)

    struct = filter_what_changed(struct)
    logger.info('{} file(s) have been added or modified.'.format(len(struct)))

    if not skip_validation and not is_valid(struct):
        logger.info("We've got problems... :(")
        sys.exit(1)

    has_published = _publish(base_url, struct, message, username, password)
    if has_published:
        logger.info("Great work!!! =D")
    else:
        logger.info("Stop the Press!!! =()")
        sys.exit(1)
