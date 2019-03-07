from copy import copy


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

    return md
