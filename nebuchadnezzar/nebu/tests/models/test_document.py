import json

from lxml import etree
from nebu.xml_utils import (
    HTML_DOCUMENT_NAMESPACES,
)

from nebu.models.document import Document


REFERENCE_MARKER = '#!--testing--'


def mock_reference_resolver(reference):
    pass


class TestDocument(object):

    def test_sanatize_content(self, datadir):
        for assembled in datadir.glob("desserts-*.xhtml"):
            with assembled.open('rb') as fb:
                html = etree.parse(fb)
                # And parse a second copy for verification
                fb.seek(0)
                expected_html = etree.parse(fb)

            # Hit the target
            results = Document._sanatize_content(html)

            # Construct expected results
            body = expected_html.xpath(
                "//xhtml:body",
                namespaces=HTML_DOCUMENT_NAMESPACES,
            )[0]
            metadata_elm = body.xpath(
                "//xhtml:div[@data-type='metadata']",
                namespaces=HTML_DOCUMENT_NAMESPACES,
            )[0]
            body.remove(metadata_elm)
            body.attrib.pop('itemtype')
            body.attrib.pop('itemscope')
            expected_results = etree.tostring(expected_html)

            assert results == expected_results

    def test_from_git_index_cnxml(self, git_collection_data, snapshot):
        filepath = git_collection_data / 'm46882' / 'index.cnxml'

        # Hit the target
        doc = Document.from_index_cnxml(filepath, mock_reference_resolver)

        # Verify the metadata
        assert doc.id == 'm46882'
        snapshot.assert_match(json.dumps(doc.metadata), "metadata.json")

        # Verify the content is content'ish
        assert doc._xml.xpath(
            "/xhtml:body/*[@data-type='metadata']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        ) == []
        assert len(doc._xml.xpath(
            "//*[@id='fs-idm20141232']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )) == 1
