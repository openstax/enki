import pytest
from copy import copy

from lxml import etree
from cnxepub.html_parsers import HTML_DOCUMENT_NAMESPACES

from nebu.models.document import Document


REFERENCE_MARKER = '#!--testing--'
M46882_METADATA = {
    'authors': [{'id': 'OpenStaxCollege',
                 'name': 'OpenStaxCollege',
                 'type': 'cnx-id'}],
    'cnx-archive-shortid': None,
    'cnx-archive-uri': 'm46882@1.17',
    'copyright_holders': [{'id': 'OSCRiceUniversity',
                           'name': 'OSCRiceUniversity',
                           'type': 'cnx-id'}],
    'created': '2013/07/19 00:42:23 -0500',
    'derived_from_title': None,
    'derived_from_uri': None,
    'editors': [],
    'illustrators': [],
    'keywords': ('cumulative relative frequency', 'frequency'),
    'language': 'en',
    'license_text': 'CC BY',
    'license_url': 'http://creativecommons.org/licenses/by/4.0/',
    'print_style': None,
    'publishers': [{'id': 'OpenStaxCollege',
                    'name': 'OpenStaxCollege',
                    'type': 'cnx-id'},
                   {'id': 'cnxstats', 'name': 'cnxstats', 'type': 'cnx-id'}],
    'revised': '2019/02/08 09:37:55.846 US/Central',
    'subjects': ('Mathematics and Statistics',),
    'summary': None,
    'title': 'Frequency, Frequency Tables, and Levels of Measurement',
    'translators': [],
    'version': '1.17',
    'canonical_book_uuid': None,
    'slug': None,
}
M46882_GIT_METADATA = {
    'authors': [],
    'cnx-archive-shortid': None,
    'cnx-archive-uri': 'm46882@None',
    'copyright_holders': [],
    'created': None,
    'derived_from_title': None,
    'derived_from_uri': None,
    'editors': [],
    'illustrators': [],
    'keywords': (),
    'language': None,
    'license_text': 'CC BY',
    'license_url': None,
    'print_style': None,
    'publishers': [],
    'revised': '2019/02/08 09:37:55.846 US/Central',
    'subjects': (),
    'summary': None,
    'title': 'Frequency, Frequency Tables, and Levels of Measurement',
    'translators': [],
    'version': 'None',
    'uuid': '3fb20c92-9515-420b-ab5e-6de221b89e99',
    'canonical_book_uuid': '30189442-6998-4686-ac05-ed152b91b9de',
    'slug': None,
}


def mock_reference_resolver(reference, resource):
    """Used for testing reference resolution during model tests"""
    if resource:
        reference.bind(resource, '{}/{{}}'.format(REFERENCE_MARKER))


class TestDocument(object):

    @pytest.mark.parametrize(
        'assembled', ['neb_assembled_data', 'git_assembled_data'])
    def test_sanatize_content(self, request, assembled):
        assembled_data = request.getfixturevalue(assembled)
        with (assembled_data / 'm46913.xhtml').open('rb') as fb:
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

    def test_find_resources(self, request, neb_collection_data):
        loc = neb_collection_data / 'm46909'

        # Hit the target
        resources = Document._find_resources(loc)

        # Verify we discovered the resource files
        expected_filenames = [
            'Prev_m16020_DotPlot.png',
            'fig-ch01_02_01n.png',
            'm16020_DotPlot_description.html',
            'm16020_DotPlot_download.pdf',
        ]
        assert sorted([r.id for r in resources]) == expected_filenames
        assert sorted([r.filename for r in resources]) == expected_filenames

    def test_from_index_cnxml(self, neb_collection_data):
        filepath = neb_collection_data / 'm46882' / 'index.cnxml'

        # Hit the target
        doc = Document.from_index_cnxml(filepath, mock_reference_resolver)

        # Verify the metadata
        assert doc.id == 'm46882'
        expected_metadata = copy(M46882_METADATA)
        # When parsing from index.cnxml, neb uses the cnxml metadata parser
        expected_metadata['uuid'] = None
        assert doc.metadata == expected_metadata

        # Verify the content is content'ish
        assert doc._xml.xpath(
            "/xhtml:body/*[@data-type='metadata']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        ) == []
        assert len(doc._xml.xpath(
            "//*[@id='fs-idm20141232']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )) == 1

        # Verify the resources are attached to the object
        expected_filenames = [
            'CNX_Stats_C01_M10_001.jpg',
            'CNX_Stats_C01_M10_002.jpg',
            'CNX_Stats_C01_M10_003.jpg',
        ]
        filenames = [r.filename for r in doc.resources]
        assert sorted(filenames) == expected_filenames

        # Verify the references have been rewritten
        ref = '{}/CNX_Stats_C01_M10_003.jpg'.format(REFERENCE_MARKER).encode()
        assert ref in doc.content
        # Verify external and non-existent resource references remain
        assert b'src="foobar.png"' in doc.content
        assert b'ef="/m10275@2.1"' in doc.content  # rewritten in cnxml->html
        assert b'ef="http://en.wikibooks.org/"' in doc.content

    def test_from_git_index_cnxml(self, git_collection_data):
        filepath = git_collection_data / 'm46882' / 'index.cnxml'

        # Hit the target
        doc = Document.from_index_cnxml(filepath, mock_reference_resolver)

        # Verify the metadata
        assert doc.id == 'm46882'
        expected_metadata = copy(M46882_GIT_METADATA)
        assert doc.metadata == expected_metadata

        # Verify the content is content'ish
        assert doc._xml.xpath(
            "/xhtml:body/*[@data-type='metadata']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        ) == []
        assert len(doc._xml.xpath(
            "//*[@id='fs-idm20141232']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )) == 1

    def test_from_filepath(self, neb_assembled_data):
        filepath = neb_assembled_data / 'm46882.xhtml'

        # Hit the target
        doc = Document.from_filepath(filepath)

        # Verify the metadata
        assert doc.id == 'm46882'
        expected_metadata = copy(M46882_METADATA)
        # cnx-epub metadata is mutable, so sequences are lists rather than
        # tuples.
        expected_metadata['keywords'] = list(expected_metadata['keywords'])
        expected_metadata['subjects'] = list(expected_metadata['subjects'])
        assert doc.metadata == expected_metadata

        # Verify the content is content'ish
        assert doc._xml.xpath(
            "/xhtml:body/*[@data-type='metadata']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        ) == []
        assert len(doc._xml.xpath(
            "//*[@id='fs-idm20141232']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )) == 1

        # Verify the resources are attached to the object
        expected_filenames = []
        filenames = [r.filename for r in doc.resources]
        assert sorted(filenames) == expected_filenames

        # Verify the references have been rewritten
        ref = '{}/CNX_Stats_C01_M10_003.jpg'.format(REFERENCE_MARKER).encode()
        assert ref in doc.content

    def test_from_git_filepath(self, git_assembled_data):
        filepath = git_assembled_data / 'm46882.xhtml'

        # Hit the target
        doc = Document.from_filepath(filepath)

        # Verify the metadata
        assert doc.id == 'm46882'
        expected_metadata = copy(M46882_GIT_METADATA)
        # cnx-epub metadata is mutable, so sequences are lists rather than
        # tuples.
        expected_metadata['keywords'] = list(expected_metadata['keywords'])
        expected_metadata['subjects'] = list(expected_metadata['subjects'])
        # Document.from_index_cnxml uses cnxml to parse metadata and then does
        # some conversions while Document.from_filepath uses cnx-epub. These
        # generate slightly different values
        del expected_metadata['uuid']
        expected_metadata.update({
            'license_text': None,
        })
        assert doc.metadata == expected_metadata

        # Verify the content is content'ish
        assert doc._xml.xpath(
            "/xhtml:body/*[@data-type='metadata']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        ) == []
        assert len(doc._xml.xpath(
            "//*[@id='fs-idm20141232']",
            namespaces=HTML_DOCUMENT_NAMESPACES,
        )) == 1
