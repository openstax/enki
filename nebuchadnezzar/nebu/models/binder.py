import re

from lxml import etree
import json
from cnxml.parse import parse_metadata as parse_cnxml_metadata
from cnxepub.models import (
    Binder as BaseBinder,
    DocumentPointer,
    TranslucentBinder,
)

from .document import Document
from .utils import (
    convert_to_model_compat_metadata,
    scan_for_id_mapping,
    scan_for_uuid_mapping,
    build_id_to_uuid_mapping,
    id_from_metadata,
)


COLLECTION_ID_TAG = '{http://cnx.rice.edu/mdml}content-id'
COLLECTION_TAG = '{http://cnx.rice.edu/collxml}collection'
SUBCOLLECTION_TAG = '{http://cnx.rice.edu/collxml}subcollection'
MODULE_TAG = '{http://cnx.rice.edu/collxml}module'
TITLE_TAG = '{http://cnx.rice.edu/mdml}title'
COLLXML_TOPIC_TAGS = (
    SUBCOLLECTION_TAG,
    MODULE_TAG,
    TITLE_TAG,
)
VERSION_ATTRIB_NAME = (
    '{http://cnx.rice.edu/system-info}version-at-this-collection-version'
)
DERIVED_FROM_TAG = '{http://cnx.rice.edu/mdml}derived-from'
DOC_TYPES = (Document, DocumentPointer,)


class Binder(BaseBinder):
    # def __init__(self, *args, **kwargs):
    #     super(Binder, self).__init__(*args, **kwargs)

    @classmethod
    def from_collection_xml(cls, filepath):
        """\
        Given a ``collection.xml`` as ``filepath``. This provides the same
        interface as :class:`cnxepub.models.Binder`, but can be created from a
        ``collection.xml`` file.

        :param filepath: location of the ``collection.xml`` file
        :type filepath: :class:`pathlib.Path`
        :return: Binder object
        :rtype: :class:`Binder`

        """
        # Create a document factory
        id_to_path_map = scan_for_id_mapping(filepath.parent)
        uuid_to_path_map = scan_for_uuid_mapping(filepath.parent)
        id_to_uuid_map = build_id_to_uuid_mapping(
            id_to_path_map,
            uuid_to_path_map
        )
        document_factory = Binder._make_document_factory(
            id_to_path_map,
            id_to_uuid_map
        )

        # Obtain metadata about the collection
        with filepath.open('rb') as fb:
            xml = etree.parse(fb)
        metadata = parse_cnxml_metadata(xml)
        metadata = convert_to_model_compat_metadata(metadata)
        id = id_from_metadata(metadata)

        # Create the object
        binder = cls(id, metadata=metadata)
        Binder._update_metadata(filepath, binder)

        parent_node = current_node = binder
        chain = [binder]

        ignoring = False

        def handler(event, elm):
            nonlocal parent_node, current_node, ignoring
            if elm.tag == DERIVED_FROM_TAG:
                if event == 'start':
                    ignoring = True
                elif event == 'end':
                    ignoring = False
            if ignoring:
                return
            if elm.tag == TITLE_TAG and event == 'start':
                title = elm.text
                if isinstance(current_node, DOC_TYPES):
                    parent_node.set_title_for_node(
                        current_node,
                        title,
                    )
                    if isinstance(current_node, DocumentPointer):
                        current_node.metadata['title'] = title
                else:
                    current_node.metadata['title'] = title
            elif elm.tag == SUBCOLLECTION_TAG:
                if event == 'start':
                    current_node = TranslucentBinder()
                    parent_node.append(current_node)
                    parent_node = current_node
                    chain.append(parent_node)
                else:
                    chain.pop()
                    parent_node = chain[-1]
            elif elm.tag == MODULE_TAG and event == 'start':
                id = elm.attrib['document']
                version = elm.attrib.get(VERSION_ATTRIB_NAME, '0.0')
                current_node = document_factory(id, version)
                parent_node.append(current_node)

        def recurse(node):
            handler('start', node)
            for child in node:
                recurse(child)
            handler('end', node)

        recurse(xml.getroot())

        return binder

    @staticmethod
    def _make_reference_resolver(id, id_to_uuid_map):

        def func(reference, resource):
            # Look for module ID with an optional version
            module_id_pattern = re.compile(r'\/(m\d{5})(@\d+[.]\d+([.]\d+)?)?')
            module_id_match = module_id_pattern.search(reference.uri)

            if resource:
                bind_id = id_to_uuid_map.get(id) or id
                reference.bind(
                    resource,
                    '{}/{{}}'.format(bind_id),
                )
            elif module_id_match:
                # SingleHTMLFormatter looks for links that start with
                # "/contents/" for intra book links.  These links are important
                # for baking to work.
                reference.uri = '/contents{}'.format(reference.uri)

                module_id = module_id_match.group(0).split('@')[0][1:]
                module_uuid = id_to_uuid_map.get(module_id)
                # We want to replace all module ID instances with UUIDs if
                # there's a mapping available.
                if module_uuid:
                    reference.uri = reference.uri.replace(
                        module_id_match.group(0),
                        '/{}'.format(module_uuid)
                    )

        return func

    @staticmethod
    def _make_document_factory(id_to_path_map, id_to_uuid_map):
        """Creates a callable for creating Document or DocumentPointer
        objects based on information provided in the id-to-path mapping
        (supplied as ``id_to_path_map``).

        :param id_to_path_map: mapping of content ids to the content filepath
        :type id_to_path_map: {str: pathlib.Path, ...}

        :param id_to_uuid_map: mapping of content ids to UUIDs
        :type id_to_uuid_map: {str: str, ...}

        """

        # FIXME Passing in a reference resolver doesn't feel like the right
        #       thing to be doing. I'm fairly certain reference resolution
        #       needs to happen external to the object as a modifying adapter.

        def factory(id, version):
            try:
                filepath = id_to_path_map[id]
            except KeyError:
                return DocumentPointer('@'.join([id, version]))
            else:
                reference_resolver = Binder._make_reference_resolver(
                    id,
                    id_to_uuid_map
                )
                document = Document.from_index_cnxml(
                    filepath,
                    reference_resolver
                )
                Binder._update_metadata(filepath, document)
                return document

        return factory

    @staticmethod
    def _update_metadata(filepath, model):
        """Updates model metadata using values from metadata.json files

        :param filepath: location of the ``collection.xml`` or ``index.cnxml``
            file
        :type filepath: :class:`pathlib.Path`

        :param model: A Binder or Document object
        :type model: :class:`Binder` or :class:`Document`

        """
        metadata_file = filepath.parent / 'metadata.json'

        if metadata_file.exists():
            with open(metadata_file) as metadata_json:
                metadata = json.load(metadata_json)
                cnx_archive_uri = '{}@{}'.format(
                    metadata['id'],
                    metadata['version']
                )
                model.metadata['cnx-archive-uri'] = cnx_archive_uri
                model.ident_hash = cnx_archive_uri
        else:
            # Fallback to trying CNXML for UUID metadata
            metadata = parse_cnxml_metadata(etree.parse(filepath.open()))
            uuid = metadata.get('uuid')
            version = metadata.get('version')
            if uuid:
                cnx_archive_uri = '{}@{}'.format(uuid, version) if version \
                    else '{}@'.format(uuid)
                model.metadata['cnx-archive-uri'] = cnx_archive_uri
                model.ident_hash = cnx_archive_uri
