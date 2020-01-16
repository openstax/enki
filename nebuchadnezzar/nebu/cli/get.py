import asyncio
from itertools import groupby
from traceback import print_tb
import sys

import click
import requests

from lxml import etree
from pathlib import Path
from aiohttp import ClientSession, ClientTimeout

from ..logger import logger
from ._common import common_params, confirm, build_archive_url, calculate_sha1
from .exceptions import (MissingContent,
                         ExistingOutputDir,
                         OldContent,
                         )


DEFAULT_REQUEST_LIMIT = 8


@click.command()
@common_params
@click.option('-d', '--output-dir', type=click.Path(),
              help="output directory name (can't previously exist)")
@click.option('-t', '--book-tree', is_flag=True,
              help="create human-friendly book-tree")
@click.option('-r', '--get-resources', is_flag=True, default=False,
              help="Also get all resources (images)")
@click.option('-l', '--request-limit', type=int, default=DEFAULT_REQUEST_LIMIT,
              help="maximum number of concurrent requests to make")
@click.argument('env')
@click.argument('col_id')
@click.argument('col_version')
@click.pass_context
def get(ctx, env, col_id, col_version, output_dir, book_tree,
        get_resources, request_limit):
    """download and expand the completezip to the current working directory"""

    base_url = build_archive_url(ctx, env)

    version = None
    req_version = col_version
    if col_version.count('.') > 1:
        full_version = col_version.split('.')
        col_version = '.'.join(full_version[:2])
        version = '.'.join(full_version[1:])

    col_hash = '{}/{}'.format(col_id, col_version)
    # Fetch metadata
    url = '{}/content/{}'.format(base_url, col_hash)

    # Create a request session with retries if there's failed DNS lookups,
    # socket connections and connection timeouts.
    # See https://stackoverflow.com/questions/33895739/
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=5)
    session.mount('https://', adapter)

    # Request the collection's metadata by requests the legacy url,
    # which is redirected to the metadata url.
    resp = session.get(url)
    if resp.status_code >= 400:
        raise MissingContent(col_id, req_version)
    col_metadata = resp.json()

    # If the response is a collated (aka baked) version of the book,
    # request the non-collated (aka raw) version instead.
    if col_metadata['collated']:
        url = resp.url + '?as_collated=False'
        resp = session.get(url)
        if resp.status_code >= 400:
            # This should never happen - indicates that only baked exists?
            raise MissingContent(col_id, req_version)
        col_metadata = resp.json()

    uuid = col_metadata['id']
    # metadata fetch used legacy IDs, so will only have
    # the latest minor version - if "version" is set, the
    # user requested an explicit minor (3 part version: 1.X.Y)
    # refetch metadata, using uuid and requested version
    if version and version != col_metadata['version']:
        url = '{}/contents/{}@{}'.format(base_url, uuid, version) + \
              '?as_collated=False'
        resp = session.get(url)
        if resp.status_code >= 400:  # Requested version doesn't exist
            raise MissingContent(col_id, req_version)
        col_metadata = resp.json()

    version = col_metadata['version']

    # Generate full output dir as soon as we have the version
    output_dir = output_dir or f'{col_id}_1.{version}'
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise ExistingOutputDir(output_dir)

    # Fetch extras (includes head and downloadable file info)
    url = '{}/extras/{}@{}'.format(base_url, uuid, version)
    resp = session.get(url)

    # Latest defaults to successfully baked - we need headVersion
    if col_version == 'latest':
        version = resp.json()['headVersion']
        url = '{}/extras/{}@{}'.format(base_url, uuid, version)
        resp = session.get(url)

    col_extras = resp.json()

    if version != col_extras['headVersion']:
        logger.warning("Fetching non-head version of {}."
                       "\n    Head: {},"
                       " requested {}".format(col_id,
                                              col_extras['headVersion'],
                                              version))
        if not(confirm("Fetch anyway? [y/n] ")):
            raise OldContent()

    # Write tree
    tree = col_metadata['tree']

    num_pages = _count_nodes(tree)
    try:
        label = f'Getting {output_dir.relative_to(Path.cwd())}'
    except ValueError:
        # Raised when output_dir is not a child of cwd
        label = f'Getting {output_dir}'
    with click.progressbar(length=num_pages,
                           label=label,
                           width=0,
                           show_pos=True) as pbar:
        loop = asyncio.get_event_loop()

        loop.set_exception_handler(report_and_quit)
        coro = _write_contents(tree,
                               base_url,
                               output_dir,
                               book_tree,
                               get_resources,
                               request_limit,
                               pbar)
        loop.run_until_complete(coro)


def report_and_quit(loop, context):  # pragma: no cover
    loop.default_exception_handler(context)

    exception = context.get('exception')
    if exception is not None:
        print(type(exception), file=sys.stderr)
        print_tb(exception.__traceback__)
        print(str(exception), file=sys.stderr)
    loop.stop()


def _count_nodes(node):
    if 'contents' in node:
        return sum([_count_nodes(child) for child in node['contents']]) + 1
    else:
        return 1


filename_by_type = {'application/vnd.org.cnx.collection': 'collection.xml',
                    'application/vnd.org.cnx.module': 'index.cnxml'}
filename_ignore = ['index.cnxml.html']


def filename_to_resource_group(filename):
    if filename in filename_ignore:
        return 'ignore'
    if filename in filename_by_type.values():
        return 'content'
    return 'extras'


def collect_groupby(groupby_obj, group_func=list):
    groups = {}
    for key, group in groupby_obj:
        groups[key] = group_func(group)
    return groups


def _safe_name(name):
    return name.replace('/', '∕').replace(':', '∶')


def store_sha1(sha1, write_dir, filename):
    with (write_dir / '.sha1sum').open('a') as s:
        s.write('{}  {}\n'.format(sha1, filename))


async def do_with_retried_request_while(session,
                                        url,
                                        condition,
                                        max_retries,
                                        do,
                                        sleep_time=0.5):
    retries = 0
    while retries <= max_retries:
        try:
            async with session.get(
                    url,
                    timeout=ClientTimeout(total=30, connect=10)) as response:
                if not condition(response):
                    return await do(response)
        except asyncio.TimeoutError:  # pragma: no cover
            pass
        retries += 1
        await asyncio.sleep(sleep_time)
    raise Exception(f'Max retries exceeded: {url}')


async def _write_contents(tree,
                          base_url,
                          out_dir,
                          book_tree=False,
                          get_resources=False,
                          request_limit=DEFAULT_REQUEST_LIMIT,
                          pbar=None):
    async def fetch_content_meta_node(session,
                                      node,
                                      content_meta_url,
                                      write_dir,
                                      index_in_group=0):
        async def get_metadata():
            async def response_json(response):
                if 500 > response.status >= 400:
                    return {}
                return await response.json()

            return await do_with_retried_request_while(
                session=session,
                url=content_meta_url,
                condition=lambda resp: resp.status in (503, 504),
                max_retries=4,
                do=response_json)

        def get_resource_groups():
            def key_func(tup):
                return filename_to_resource_group(tup[0])

            if metadata == {}:
                return {}

            by_filename = {res['filename']: res
                           for res in metadata['resources']}
            by_resource_group = collect_groupby(
                groupby(sorted(list(by_filename.items()), key=key_func),
                        key_func),
                dict)
            return by_resource_group

        def enqueue_content():
            if 'content' not in resource_groups:
                return

            content_id = resource_groups['content'][content_filename]['id']
            content_url = f'{base_url}/resources/{content_id}'
            content_coro = fetch_content_node(session,
                                              content_url,
                                              write_dir,
                                              content_filename)
            tasks.append(asyncio.ensure_future(content_coro))

        def enqueue_extras():
            if not get_resources:
                return
            if 'extras' not in resource_groups:
                return

            for filename, meta in resource_groups['extras'].items():
                resource_id = meta['id']
                resource_url = f'{base_url}/resources/{resource_id}'
                resource_coro = fetch_resource_node(session,
                                                    resource_url,
                                                    write_dir,
                                                    filename,
                                                    resource_id)
                tasks.append(asyncio.ensure_future(resource_coro))

        def enqueue_children():
            def is_preface(node):
                return ("Preface" in node['title'])

            if 'contents' not in node:
                return

            no_bump_index = is_preface(node['contents'][0])
            for index, child in enumerate(node['contents']):
                content_meta_url = f'{base_url}/contents/{child["id"]}'
                content_meta_coro = fetch_content_meta_node(session,
                                                            child,
                                                            content_meta_url,
                                                            write_dir,
                                                            (index
                                                             if no_bump_index
                                                             else index + 1))
                tasks.append(asyncio.ensure_future(content_meta_coro))

        def get_scoped_directory():
            is_module = content_filename == 'index.cnxml'
            is_collection = content_filename == 'collection.xml'

            node_title = node.get('title', '')
            index_string = ('{:02d} '.format(index_in_group)
                            if not is_collection
                            else '')
            tree_dirname = f'{index_string}{_safe_name(node_title)}'

            if is_module and not book_tree and legacy_id is not None:
                return legacy_id
            if book_tree:
                return tree_dirname
            return ''

        tasks = []

        await semaphore.acquire()
        metadata = await get_metadata()
        semaphore.release()

        resource_groups = get_resource_groups()

        media_type = metadata.get('mediaType')
        content_filename = filename_by_type.get(media_type)
        legacy_id = metadata.get('legacy_id')

        scoped_directory = get_scoped_directory()
        write_dir = write_dir / scoped_directory
        write_dir.mkdir(parents=True, exist_ok=True)

        enqueue_content()
        enqueue_extras()
        enqueue_children()

        await asyncio.wait(tasks)

        if pbar is not None:
            pbar.update(1)
        return

    async def fetch_resource_node(session,
                                  resource_url,
                                  write_dir,
                                  filename,
                                  resource_id):
        await semaphore.acquire()

        async def read_response(response):
            return await response.read()
        resp = await do_with_retried_request_while(
            session=session,
            url=resource_url,
            condition=lambda resp: resp.status in (503, 504),
            max_retries=4,
            do=read_response)
        filepath = write_dir / filename
        filepath.write_bytes(resp)
        store_sha1(resource_id, write_dir, filename)

        semaphore.release()

    async def fetch_content_node(session,
                                 content_url,
                                 write_dir,
                                 filename):
        await semaphore.acquire()

        async def read_response(response):
            return await response.read()
        resp = await do_with_retried_request_while(
            session=session,
            url=content_url,
            condition=lambda resp: resp.status in (503, 504),
            max_retries=4,
            do=read_response)
        filepath = write_dir / filename
        filepath.write_bytes(etree.tostring(etree.XML(resp),
                                            encoding='utf-8'))
        sha1 = calculate_sha1(write_dir / filename)
        store_sha1(sha1, write_dir, filename)

        semaphore.release()

    initial_url = f'{base_url}/contents/{tree["id"]}'

    session = ClientSession(headers={"Connection": "close"})
    semaphore = asyncio.Semaphore(request_limit)
    coro = fetch_content_meta_node(session, tree, initial_url, out_dir)

    await asyncio.ensure_future(coro)
    await session.close()
