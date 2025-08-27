from enum import Enum
from typing import Optional

from ..converters import etree_cnxml_to_full_html
from ..xml_utils import open_xml, etree_from_str, Elementish, xpath_html
from ..parse import parse_metadata


COLLECTION_TAG = "{http://cnx.rice.edu/collxml}collection"
SUBCOLLECTION_TAG = "{http://cnx.rice.edu/collxml}subcollection"
MODULE_TAG = "{http://cnx.rice.edu/collxml}module"
TITLE_TAG = "{http://cnx.rice.edu/mdml}title"


class PartType(Enum):
    COLLECTION = 0
    SUBCOL = 1
    DOCUMENT = 2


class BookPart:
    type: PartType
    metadata: dict[str, Optional[str | dict]]
    children: list["BookPart"]
    content: Optional[Elementish]

    def __init__(self, type, metadata, content=None):
        self.type = type
        self.metadata = metadata
        self.children = []
        self.content = content

    @property
    def is_col(self):
        return self.type == PartType.COLLECTION

    @property
    def is_subcol(self):
        return self.type == PartType.SUBCOL

    @property
    def is_doc(self):
        return self.type == PartType.DOCUMENT

    @property
    def is_super(self):
        return self.is_doc and self.content is not None and 0 != len(
            xpath_html(self.content, '//xhtml:body[contains(@class, "super")]')
        )

    @property
    def documents(self):
        return self.get_parts_by_type(PartType.DOCUMENT)

    def flatten(self):
        def recurse(book_part):
            for book_part in book_part.children:
                yield book_part
                if book_part.is_subcol:
                    for child_part in recurse(book_part):
                        yield child_part

        yield self
        for child_part in recurse(self):
            yield child_part

    def get_parts_by_type(self, part_type):
        for book_part in self.flatten():
            if book_part.type == part_type:
                yield book_part

    @staticmethod
    def doc_from_file(p):
        cnxml = open_xml(p)
        metadata = parse_metadata(cnxml)
        html = etree_from_str(etree_cnxml_to_full_html(cnxml).encode())
        doc = BookPart(PartType.DOCUMENT, metadata, html)
        return doc

    @staticmethod
    def collection_from_file(filepath, path_resolver):
        """\
        Given a ``collection.xml`` as ``filepath``.

        :param filepath: location of the ``collection.xml`` file
        :type filepath: :class:`pathlib.Path`
        :return: BookPart object
        :rtype: :class:`BookPart`

        """

        doc_by_id = {}
        doc_by_uuid = {}

        def new_col():
            cnxml = open_xml(str(filepath))
            metadata = parse_metadata(cnxml)
            return BookPart(PartType.COLLECTION, metadata)

        def new_subcol():
            return BookPart(PartType.SUBCOL, {})

        def new_doc(id):
            doc = BookPart.doc_from_file(path_resolver.get_module_path(id))
            doc_by_id[id] = doc_by_uuid[doc.metadata["uuid"]] = doc
            return doc

        # Obtain metadata about the collection
        with open(filepath, "rb") as fb:
            xml = open_xml(fb)

        root_part = parent_part = current_part = new_col()
        parent_stack = []

        def handler(event, elm):
            nonlocal parent_part, current_part
            if elm.tag == TITLE_TAG and event == "start":
                title = elm.text
                assert (
                    not current_part.is_doc
                ), "Document pointers are not longer supported"
                current_part.metadata["title"] = title
            elif elm.tag == SUBCOLLECTION_TAG:
                if event == "start":
                    current_part = new_subcol()
                    parent_part.children.append(current_part)
                    parent_stack.append(parent_part)
                    parent_part = current_part
                else:
                    parent_part = parent_stack.pop()
            elif elm.tag == MODULE_TAG and event == "start":
                id = elm.attrib["document"]
                current_part = new_doc(id)
                parent_part.children.append(current_part)

        def recurse(elem):
            handler("start", elem)
            for child in elem:
                recurse(child)
            handler("end", elem)

        recurse(xml.getroot())

        return (root_part, doc_by_id, doc_by_uuid)
