from nebu.models.base_binder import (
    flatten_to_documents,
    model_to_tree,
)

from nebu.models.binder import Binder


class TestBinder(object):

    def test_from_git_collection_xml(self, git_collection_data):
        filepath = git_collection_data / 'collection.xml'

        # Hit the target
        binder = Binder.from_collection_xml(filepath)

        # Verify the tree structure
        expected_tree = {
            'contents': [
                {'id': 'm47830@1.17',
                 'shortId': None,
                 'title': 'Preface'},
                {'contents': [{'id': 'd93df8ff-6e4a-4a5e-befc-ba5a144f309c@',
                               'shortId': None,
                               'title': 'Introduction'},
                              {'id': 'cb418599-f69b-46c1-b0ef-60d9e36e677f@',
                               'shortId': None,
                               'title': 'Definitions of '
                               'Statistics, Probability, '
                               'and Key Terms'},
                              {'id': 'm46885@1.21',
                               'shortId': None,
                               'title': 'Data, Sampling, and '
                               'Variation in Data and '
                               'Sampling'},
                              {'id': '3fb20c92-9515-420b-ab5e-6de221b89e99@',
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
            'id': '30189442-6998-4686-ac05-ed152b91b9de@af89d35',
            'shortId': None,
            'title': 'Introductory Statistics',
        }
        assert model_to_tree(binder) == expected_tree

        # Verify the metadata
        expected_metadata = {
            'cnx-archive-shortid': None,
            'cnx-archive-uri': '30189442-6998-4686-ac05-ed152b91b9de@af89d35',
            'language': None,
            'license_text': 'Creative Commons Attribution License',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'revised': '2019-02-22T14:15:14.840187-06:00',
            'summary': None,
            'title': 'Introductory Statistics',
            'version': 'af89d35',
            'uuid': '30189442-6998-4686-ac05-ed152b91b9de',
            'canonical_book_uuid': None,
            'slug': 'introductory-statistics',
        }
        assert binder.metadata == expected_metadata

        # Verify documents have been created
        expected = [
            'd93df8ff-6e4a-4a5e-befc-ba5a144f309c',
            'cb418599-f69b-46c1-b0ef-60d9e36e677f',
            '3fb20c92-9515-420b-ab5e-6de221b89e99'
        ]
        assert [x.id for x in flatten_to_documents(binder)] == expected

        # Verify the collection title overrides
        custom_title_doc = [
            doc
            for doc in flatten_to_documents(binder)
            if doc.id == 'd93df8ff-6e4a-4a5e-befc-ba5a144f309c'
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

        # Verify cnx-archive-uri is set in modules with metadata
        expected = {
            '3fb20c92-9515-420b-ab5e-6de221b89e99':
                '3fb20c92-9515-420b-ab5e-6de221b89e99@',
            'cb418599-f69b-46c1-b0ef-60d9e36e677f':
                'cb418599-f69b-46c1-b0ef-60d9e36e677f@',
            'd93df8ff-6e4a-4a5e-befc-ba5a144f309c':
                'd93df8ff-6e4a-4a5e-befc-ba5a144f309c@'
        }
        for doc in flatten_to_documents(binder):
            assert expected.get(doc.id)
            assert expected[doc.id] == doc.metadata['cnx-archive-uri']
