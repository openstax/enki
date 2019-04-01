from pathlib import Path

from lxml import etree
from cnxepub.html_parsers import (
    HTML_DOCUMENT_NAMESPACES,
    parse_metadata,
)
from cnxepub.models import (
    Document as BaseDocument,
)
from cnxml.parse import parse_metadata as parse_cnxml_metadata
from cnxtransforms import cnxml_to_full_html

from .resource import FileSystemResource
from .utils import convert_to_model_compat_metadata, id_from_metadata

# A list of filenames to ignore while attempting to discover
# resources in a directory.
IGNORE_RESOURCES_BY_FILENAME = (
    '.sha1sum',
    'index.cnxml',
)


class Document(BaseDocument):

    def __init__(self, *args, **kwargs):
        self._reference_resolver = kwargs.get('reference_resolver')
        super(Document, self).__init__(*args, **kwargs)

        # Resolve the references before returning the object
        self.resolve_references()

    @classmethod
    def from_index_cnxml(cls, filepath, reference_resolver):
        """\
        Given a ``index.cnxml`` as ``filepath``. This provides the same
        interface as :class:`cnxepub.models.Document`, but can be created
        from file.

        Note, the ``reference_resolver`` is a function that accepts the
        reference and resource as it's arguments. It's the resolver's
        responsibility to *bind* the reference to the resource.

        :param filepath: location of the ``index.cnxml``
        :type filepath: :class:`pathlib.Path`
        :param reference_resolver: function used to resolve references
        :type reference_resolver: func
        :return: Document object
        :rtype: :class:`Document`

        """
        # Parse to xml for metadata extraction
        with filepath.open('rb') as fb:
            cnxml = etree.parse(fb)
        # Transform and parse to html for model creation
        with filepath.open('r') as fb:
            html = etree.fromstring(cnxml_to_full_html(fb.read()).encode())

        resources = []
        metadata = parse_cnxml_metadata(cnxml)
        metadata = convert_to_model_compat_metadata(metadata)
        id = id_from_metadata(metadata)

        # Clean and sanatize the content
        content = cls._sanatize_content(html)

        # Process the resource file
        resources = cls._find_resources(filepath.parent)

        # Create the object
        return cls(id, content, metadata=metadata, resources=resources,
                   reference_resolver=reference_resolver)

    @classmethod
    def from_filepath(cls, filepath):
        """\
        Given a html document as ``filepath``. This provides the same
        interface as :class:`cnxepub.models.Document`, but can be created
        from file.

        :param filepath: location of the ``index.cnxml``
        :type filepath: :class:`pathlib.Path`
        :return: Document object
        :rtype: :class:`Document`

        """
        with filepath.open('rb') as fb:
            html = etree.parse(fb)

        resources = []
        metadata = parse_metadata(html)
        id = id_from_metadata(metadata)

        # Clean and sanatize the content
        content = cls._sanatize_content(html)

        # This method will not process resources because it can not assume
        # to know where the resources are. If loading of resources is needed,
        # please load the resources from the references after instantiation.

        # Create the object
        return cls(id, content, metadata=metadata, resources=resources)

    @staticmethod
    def _sanatize_content(html):
        """\
        Sanatize the given HTML (as ``html``) of metadata.

        :param html: element tree representing the document
        :type html: etree.ElementTree
        :return: html as a string
        :rtype: str

        """
        body = html.xpath(
            '//xhtml:body',
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )[0]
        metadata_nodes = html.xpath(
            "//xhtml:body/*[@data-type='metadata']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )
        for node in metadata_nodes:
            body.remove(node)
        for key in body.keys():
            if key in ('itemtype', 'itemscope'):
                body.attrib.pop(key)
        return etree.tostring(html)

    @staticmethod
    def _find_resources(loc):
        """Given a location to look for resources, create and return a list of
        :class:`cnxepub.models.Resource` objects.

        :param loc: location to look for resource files
        :type loc: :class:`pathlib.Path`
        :return: list of Resources
        :rtype: [:class:`cnxepub.models.Resource`]

        """
        resources = []
        for filepath in loc.glob('*'):
            if filepath.name in IGNORE_RESOURCES_BY_FILENAME:
                continue
            resources.append(FileSystemResource(filepath))
        return resources

    def resolve_references(self):
        """\
        Resolve the object's internal references if we have a resource that
        matches the reference's filename.

        """
        if self._reference_resolver is None:
            # Without a resolver this method can't do anything.
            return

        for ref in self.references:
            if ref.remote_type == 'external':
                continue
            name = Path(ref.uri).name
            try:
                resource = [r for r in self.resources if r.filename == name][0]
            except IndexError:
                # When resources are missing, the problem is pushed off
                # to the rendering process, which will
                # raise a missing reference exception when necessary.
                resource = None
            self._reference_resolver(ref, resource)
