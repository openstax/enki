import re

from lxml import etree
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
        document_factory = Binder._make_document_factory(id_to_path_map)

        # Obtain metadata about the collection
        with filepath.open('rb') as fb:
            xml = etree.parse(fb)
        metadata = parse_cnxml_metadata(xml)
        metadata = convert_to_model_compat_metadata(metadata)
        id = id_from_metadata(metadata)

        # Create the object
        binder = cls(id, metadata=metadata)

        # Load the binder using the collection tree
        with filepath.open('rb') as fb:
            elm_iterparser = etree.iterparse(
                fb,
                events=('start', 'end'),
                tag=COLLXML_TOPIC_TAGS,
                remove_blank_text=True,
            )

            parent_node = current_node = binder
            chain = [binder]
            for event, elm in elm_iterparser:
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
                    version = elm.attrib[VERSION_ATTRIB_NAME]
                    current_node = document_factory(id, version)
                    parent_node.append(current_node)
        return binder

    @staticmethod
    def _make_reference_resolver(id):

        def func(reference, resource):
            if resource:
                reference.bind(
                    resource,
                    '{}/{{}}'.format(id),
                )
            elif re.match('/m[0-9]+.*', reference.uri):
                # SingleHTMLFormatter looks for links that start with
                # "/contents/" for intra book links.  These links are important
                # for baking to work.
                reference.uri = '/contents{}'.format(reference.uri)

        return func

    @staticmethod
    def _make_document_factory(id_to_path_map):
        """Creates a callable for creating Document or DocumentPointer
        objects based on information provided in the id-to-path mapping
        (supplied as ``id_to_path_map``).

        :param id_to_path_map: mapping of content ids to the content filepath
        :type id_to_path_map: {str: pathlib.Path, ...}

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
                reference_resolver = Binder._make_reference_resolver(id)
                return Document.from_index_cnxml(filepath, reference_resolver)

        return factory
