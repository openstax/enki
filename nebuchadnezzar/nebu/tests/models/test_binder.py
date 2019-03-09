from cnxepub.models import (
    flatten_to_documents,
    model_to_tree,
)

from nebu.models.binder import Binder


class TestBinder(object):

    def test_from_collection_xml(self, collection_data):
        filepath = collection_data / 'collection.xml'

        # Hit the target
        binder = Binder.from_collection_xml(filepath)

        # Verify the tree structure
        expected_tree = {
            'contents': [
                {'id': 'm47830@1.17',
                 'shortId': None,
                 'title': 'Preface'},
                {'contents': [{'id': 'm46913@1.13',
                               'shortId': None,
                               'title': 'Introduction'},
                              {'id': 'm46909@1.12',
                               'shortId': None,
                               'title': 'Definitions of '
                               'Statistics, Probability, '
                               'and Key Terms'},
                              {'id': 'm46885@1.21',
                               'shortId': None,
                               'title': 'Data, Sampling, and '
                               'Variation in Data and '
                               'Sampling'},
                              {'id': 'm46882@1.17',
                               'shortId': None,
                               'title': 'Frequency, Frequency '
                               'Tables, and Levels of '
                               'Measurement'},
                              {'id': 'm46919@1.13',
                               'shortId': None,
                               'title': 'Experimental Design and '
                               'Ethics'}],
                 'id': 'subcol',
                 'shortId': None,
                 'title': 'Sampling and Data'},
                {'contents': [{'id': 'm46925@1.7',
                               'shortId': None,
                               'title': 'Introduction'},
                              {'id': 'm46934@1.10',
                               'shortId': None,
                               'title': 'Stem-and-Leaf Graphs '
                               '(Stemplots), Line Graphs, '
                               'and Bar Graphs'}],
                 'id': 'subcol',
                 'shortId': None,
                 'title': 'Descriptive Statistics'},
                {'id': 'm47864@1.17',
                 'shortId': None,
                 'title': 'Review Exercises (Ch 3-13)'},
                {'id': 'm47865@1.16',
                 'shortId': None,
                 'title': 'Practice Tests (1-4) and Final Exams'},
                {'id': 'm47873@1.9',
                 'shortId': None,
                 'title': 'Data Sets'}],
            'id': 'col11562@1.23',
            'shortId': None,
            'title': 'Introductory Statistics',
        }
        assert model_to_tree(binder) == expected_tree

        # Verify the metadata
        expected_metadata = {
            'authors': [{'id': 'OpenStaxCollege',
                         'name': 'OpenStaxCollege',
                         'type': 'cnx-id'}],
            'cnx-archive-shortid': None,
            'cnx-archive-uri': 'col11562@1.23',
            'copyright_holders': [{'id': 'OpenStaxCollege',
                                   'name': 'OpenStaxCollege',
                                   'type': 'cnx-id'}],
            'created': '2013-07-18T19:30:26-05:00',
            'derived_from_title': None,
            'derived_from_uri': None,
            'editors': [],
            'illustrators': [],
            'keywords': (),
            'language': 'en',
            'license_text': 'CC BY',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'print_style': 'statistics',
            'publishers': [{'id': 'OpenStaxCollege',
                            'name': 'OpenStaxCollege',
                            'type': 'cnx-id'},
                           {'id': 'cnxstats',
                            'name': 'cnxstats',
                            'type': 'cnx-id'}],
            'revised': '2019-02-22T14:15:14.840187-06:00',
            'subjects': ('Mathematics and Statistics',),
            'summary': None,
            'title': 'Introductory Statistics',
            'translators': [],
            'version': '1.23',
        }
        assert binder.metadata == expected_metadata

        # Verify documents have been created
        expected = ['m46913', 'm46909', 'm46882']
        assert [x.id for x in flatten_to_documents(binder)] == expected

        # Verify the collection title overrides
        custom_title_doc = [
            doc
            for doc in flatten_to_documents(binder)
            if doc.id == 'm46913'
        ][0]
        # the page believes its title is...
        title = 'Introduction to Statistics'
        assert custom_title_doc.metadata['title'] == title
        # ...and the book believes the title is...
        title = 'Introduction'
        assert binder[1].get_title_for_node(custom_title_doc) == title

        # Verify the DocumentPointer objects have a title set on the object
        doc_pt = binder[0]
        title = 'Preface'
        assert doc_pt.metadata['title'] == title
