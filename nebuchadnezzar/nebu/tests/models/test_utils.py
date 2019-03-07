from nebu.models.utils import convert_to_model_compat_metadata


def test_convert_to_model_compat_metadata():
    # Tests covertion of the output of `cnxml.parse:parse_metadata` to
    # a structure compatible with cnx-epub's expectations.
    metadata = {
        'abstract': 'Abstract',
        'authors': ('OpenStaxCollege',),
        'created': '2012/01/23 13:03:30.293 US/Central',
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': ('key', 'words'),
        'language': 'en',
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'licensors': ('OSCRiceUniversity',),
        'maintainers': ('OpenStaxCollege', 'cnxcap'),
        'print_style': 'ccap-physics',
        'revised': '2015/07/27 12:55:32.442 GMT-5',
        'subjects': ('Mathematics and Statistics', 'Science and Technology'),
        'title': 'College Physics',
        'version': '1.9',
    }

    # Call the target
    converted_metadata = convert_to_model_compat_metadata(metadata)

    expected_metadata = {
        'authors': [
            {'id': 'OpenStaxCollege',
             'name': 'OpenStaxCollege',
             'type': 'cnx-id',
             },
        ],
        'cnx-archive-shortid': None,
        'cnx-archive-uri': 'col11406@1.9',
        'copyright_holders': [
            {'id': 'OSCRiceUniversity',
             'name': 'OSCRiceUniversity',
             'type': 'cnx-id',
             },
        ],
        'created': '2012/01/23 13:03:30.293 US/Central',
        'derived_from_title': None,
        'derived_from_uri': None,
        'editors': [],
        'illustrators': [],
        'keywords': ('key', 'words'),
        'language': 'en',
        'license_text': 'CC BY',
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'print_style': 'ccap-physics',
        'publishers': [
            {'id': 'OpenStaxCollege',
             'name': 'OpenStaxCollege',
             'type': 'cnx-id',
             },
            {'id': 'cnxcap',
             'name': 'cnxcap',
             'type': 'cnx-id',
             },
        ],
        'revised': '2015/07/27 12:55:32.442 GMT-5',
        'subjects': ('Mathematics and Statistics', 'Science and Technology'),
        'summary': 'Abstract',
        'title': 'College Physics',
        'translators': [],
        'version': '1.9',
    }
    assert converted_metadata == expected_metadata
