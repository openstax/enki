from copy import copy

import json
from cnxepub.utils import squash_xml_to_text
from cnxml.parse import parse_metadata as parse_cnxml_metadata
from cnxtransforms import cnxml_abstract_to_html
from lxml import etree


__all__ = (
    'convert_to_model_compat_metadata',
    'scan_for_id_mapping',
    'scan_for_uuid_mapping',
    'build_id_to_uuid_mapping',
    'id_from_metadata',
)


ACTORS_MAPPING_KEYS = (
    # (<litezip name>, <cnx-epub name>),
    ('authors', 'authors'),
    ('licensors', 'copyright_holders'),
    ('maintainers', 'publishers'),
)


def _format_actors(actors):
    """Format the actors list of usernames to a cnx-epub compatable format"""
    formatted_actors = []
    for a in actors:
        formatted_actors.append({'id': a, 'type': 'cnx-id', 'name': a})
    return formatted_actors


def convert_to_model_compat_metadata(metadata):
    """\
    Convert the metadata to cnx-epub model compatible metadata.
    This creates a copy of the metadata. It does not mutate the given
    metadata.

    :param metadata: metadata
    :type metadata: dict
    :return: metadata
    :rtype: dict

    """
    md = copy(metadata)

    md.setdefault('cnx-archive-shortid', None)
    md.setdefault('cnx-archive-uri', '{}@{}'.format(md['id'], md['version']))
    md.pop('id')
    # FIXME cnx-epub has an issue rendering and parsing license_text set to
    #       None, so hard code it to 'CC BY' for now.
    md.setdefault('license_text', 'CC BY')
    md.setdefault('print_style', None)

    md['derived_from_title'] = md['derived_from']['title']
    md['derived_from_uri'] = md['derived_from']['uri']
    md.pop('derived_from')

    # Translate to a Person Info structure
    for lz_key, epub_key in ACTORS_MAPPING_KEYS:
        md[epub_key] = _format_actors(md.pop(lz_key))

    md.setdefault('editors', [])
    md.setdefault('illustrators', [])
    md.setdefault('translators', [])

    md['summary'] = md.pop('abstract')
    md['summary'] = md['summary'] and md['summary'] or None
    if md['summary'] is not None:
        s = cnxml_abstract_to_html(md['summary'])
        s = etree.fromstring(s)
        md['summary'] = squash_xml_to_text(s, remove_namespaces=True)
    return md


def id_from_metadata(metadata):
    """Given an model's metadata, discover the id."""
    identifier = "cnx-archive-uri"
    return metadata.get(identifier)


def scan_for_id_mapping(start_dir):
    """Collect a mapping of content ids to filepaths relative to the given
    directory (as ``start_dir``).

    This is necessary because the filesystem could be organized as
    a `book-tree`, which is a hierarchy of directories that are labeled
    by title rather than by id.

    :param start_dir: a directory to start the scan from
    :type start_dir: :class:`pathlib.Path`
    :return: mapping of content ids to the content filepath
    :rtype: {str: pathlib.Path, ...}

    """
    mapping = {}
    for filepath in start_dir.glob('**/index.cnxml'):
        with filepath.open('rb') as fb:
            xml = etree.parse(fb)
        md = convert_to_model_compat_metadata(parse_cnxml_metadata(xml))
        id = id_from_metadata(md)
        id = id.split('@')[0]
        mapping[id] = filepath
    return mapping


def scan_for_uuid_mapping(start_dir):
    """Collect a mapping of content UUIDs to filepaths relative to the given
    directory (as ``start_dir``).

    This is similar to ``scan_for_id_mapping``, but instead of using the ID
    value found in CNXML as the key, we want the same mapping keyed by the
    UUID in the corresponding metadata.json file if it's available.

    :param start_dir: a directory to start the scan from
    :type start_dir: :class:`pathlib.Path`
    :return: mapping of content uuids to the content filepath
    :rtype: {str: pathlib.Path, ...}

    """
    mapping = {}
    for filepath in start_dir.glob('**/index.cnxml'):
        metadata_file = filepath.parent / 'metadata.json'

        if metadata_file.exists():
            with metadata_file.open('r') as metadata_json:
                metadata = json.load(metadata_json)
            uuid = metadata['id']
            mapping[uuid] = filepath
        else:
            # Fallback to trying CNXML for UUID metadata
            metadata = parse_cnxml_metadata(etree.parse(filepath.open()))
            uuid = metadata.get('uuid')
            if uuid:
                mapping[uuid] = filepath

    return mapping


def build_id_to_uuid_mapping(id_to_path_map, uuid_to_path_map):
    """Build a mapping of ID to UUID values based upon matching paths

    :param id_to_path_map: A mapping of IDs (m12345) to filepaths
    :type id_to_path_map: {str: pathlib.Path, ...}

    :param uuid_to_path_map: A mapping of UUIDs to filepaths
    :type uuid_to_path_map: {str: pathlib.Path, ...}

    :return: mapping of ids to uuids
    :rtype: {str: str, ...}

    """
    mapping = {}

    path_to_uuid_map = {
        str(path): uuid for uuid, path in uuid_to_path_map.items()
    }

    for id, path in id_to_path_map.items():
        mapping[id] = path_to_uuid_map.get(str(path))

    return mapping
