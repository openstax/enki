import pytest
from copy import copy
from pathlib import Path

from nebu.models.utils import (
    convert_to_model_compat_metadata,
    id_from_metadata,
    scan_for_id_mapping,
    scan_for_uuid_mapping,
    build_id_to_uuid_mapping,
)


class TestConvertToModelCompatMetadata(object):

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
        'subjects': (
            'Mathematics and Statistics',
            'Science and Technology',
        ),
        'title': 'College Physics',
        'version': '1.9',
    }

    def test_basic_metadata(self):
        # Tests covertion of the output of `cnxml.parse:parse_metadata` to
        # a structure compatible with cnx-epub's expectations.

        # Call the target
        converted_metadata = convert_to_model_compat_metadata(self.metadata)

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
            'subjects': (
                'Mathematics and Statistics',
                'Science and Technology',
            ),
            'summary': 'Abstract',
            'title': 'College Physics',
            'translators': [],
            'version': '1.9',
        }
        assert converted_metadata == expected_metadata

    def test_with_cnxml_in_summary(self):
        metadata = copy(self.metadata)

        # Put cnxml and math in the summary
        metadata['abstract'] = (
            "In this section you will:<list><item>A</item><item>B</item>"
            "<item><m:math><m:mi>x</m:mi></m:math></item>"
            "<item><m:math><m:mi>y</m:mi></m:math></item></list>"
        )

        # Call the target
        converted_metadata = convert_to_model_compat_metadata(metadata)

        expected_summary = (
            'In this section you will:'
            '<ul><li>A</li><li>B</li>'
            '<li><math display="inline"><semantics><mrow><mi>x</mi></mrow>'
            '<annotation-xml encoding="MathML-Content"><mi>x</mi>'
            '</annotation-xml></semantics></math></li>'
            '<li><math display="inline"><semantics><mrow><mi>y</mi></mrow>'
            '<annotation-xml encoding="MathML-Content"><mi>y</mi>'
            '</annotation-xml></semantics></math></li>'
            '</ul>'
        )
        assert converted_metadata['summary'] == expected_summary


def test_id_from_metadata():
    assert id_from_metadata({}) is None
    id = 'foo@bar'
    assert id_from_metadata({'cnx-archive-uri': id}) == id


def test_id_to_uuid_mapping():
    id_to_path_map = {
        'm46882': Path('m46882/index.cnxml'),
        'm46909': Path('m46909/index.cnxml'),
        'm37151': Path(
            '04 Lab 3-1 Basic MSP430 Assembly from Roots in LC-3/'
            'index.cnxml'),
        'm12345': Path('m12345/index.cnxml'),
    }

    uuid_to_path_map = {
        '3fb20c92-9515-420b-ab5e-6de221b89e99': Path('m46882/index.cnxml'),
        'cb418599-f69b-46c1-b0ef-60d9e36e677f': Path('m46909/index.cnxml'),
        '06ca2321-54e8-4f28-8516-f38c8e39cac7': Path(
            '04 Lab 3-1 Basic MSP430 Assembly from Roots in LC-3/'
            'index.cnxml'),
    }

    id_to_uuid_map = build_id_to_uuid_mapping(id_to_path_map, uuid_to_path_map)

    assert id_to_uuid_map['m46882'] == '3fb20c92-9515-420b-ab5e-6de221b89e99'
    assert id_to_uuid_map['m46909'] == 'cb418599-f69b-46c1-b0ef-60d9e36e677f'
    assert id_to_uuid_map['m37151'] == '06ca2321-54e8-4f28-8516-f38c8e39cac7'
    assert id_to_uuid_map.get('m12345') is None


class TestScanForIdMapping(object):

    def relpaths(self, i, start):
        k, v = i
        v = v.relative_to(start)
        return (k, v,)

    def make_results_relative(self, results, start):
        return {
            k: v.relative_to(start)
            for k, v in results.items()
        }

    @pytest.mark.parametrize(
        'collection', ['neb_collection_data', 'git_collection_data'])
    def test(self, request, collection):
        # Call the target
        collection_data = request.getfixturevalue(collection)
        id_to_path_mapping = scan_for_id_mapping(collection_data)

        # Check the results
        expected = {
            'm46882': Path('m46882/index.cnxml'),
            'm46909': Path('m46909/index.cnxml'),
            'm46913': Path('m46913/index.cnxml'),
        }
        results = self.make_results_relative(
            id_to_path_mapping,
            collection_data,
        )
        assert results == expected

    def test_book_tree_structure(self, datadir):
        loc = (
            datadir / 'book_tree' /
            'Intro to Computational Engineering∶ Elec 220 Labs'
        )

        # Call the target
        id_to_path_mapping = scan_for_id_mapping(loc)

        # Check the results
        expected = {
            'm37151': Path(
                '04 Lab 3-1 Basic MSP430 Assembly from Roots in LC-3/'
                'index.cnxml'),
            'm37152': Path(
                '10 Helpful General Information/'
                '01 MSP430 LaunchPad Test Circuit Breadboarding Instructions/'
                'index.cnxml'),
            'm37154': Path(
                '10 Helpful General Information/'
                '02 A Student to Student Intro to IDE '
                'Programming and CCS4/index.cnxml'),
            'm37217': Path(
                '06 Lab 4-1 Interrupt Driven Programming in MSP430 Assembly/'
                'index.cnxml'),
            'm37386': Path(
                '08 Lab 5-1 C Language Programming through the ADC '
                'and the MSP430/index.cnxml'),
            'm40643': Path(
                '05 Lab 3-2 Digital Input and Output with the MSP430/'
                'index.cnxml'),
            'm40645': Path(
                '07 Lab 4-2 Putting It All Together/index.cnxml'),
            'm40646': Path(
                '09 Lab 5-2 Using C and the ADC for "Real World" '
                'Applications with the MSP430/index.cnxml'),
            'm42302': Path(
                '02 A Quartus Project from Start to Finish∶ '
                '2 Bit Mux Tutorial/index.cnxml'),
            'm42303': Path(
                '01 Introduction to Quartus and Circuit Diagram Design/'
                'index.cnxml'),
            'm42304': Path(
                '03 Lab 1-1∶ 4-Bit Mux and all NAND∕NOR Mux/index.cnxml'),
        }
        results = self.make_results_relative(id_to_path_mapping, loc)
        assert results == expected


class TestScanForUUIDMapping(object):

    def relpaths(self, i, start):
        k, v = i
        v = v.relative_to(start)
        return (k, v,)

    def make_results_relative(self, results, start):
        return {
            k: v.relative_to(start)
            for k, v in results.items()
        }

    @pytest.mark.parametrize(
        'collection', ['neb_collection_data', 'git_collection_data'])
    def test(self, request, collection):
        collection_data = request.getfixturevalue(collection)
        # Call the target
        uuid_to_path_mapping = scan_for_uuid_mapping(collection_data)

        # Check the results
        expected = {
            '3fb20c92-9515-420b-ab5e-6de221b89e99': Path('m46882/index.cnxml'),
            'cb418599-f69b-46c1-b0ef-60d9e36e677f': Path('m46909/index.cnxml'),
            'd93df8ff-6e4a-4a5e-befc-ba5a144f309c': Path('m46913/index.cnxml'),
        }
        results = self.make_results_relative(
            uuid_to_path_mapping,
            collection_data,
        )
        assert results == expected

    def test_book_tree_structure(self, datadir):
        loc = (
            datadir / 'book_tree' /
            'Intro to Computational Engineering∶ Elec 220 Labs'
        )

        # Call the target
        uuid_to_path_mapping = scan_for_uuid_mapping(loc)

        # Check the results
        expected = {
            '06ca2321-54e8-4f28-8516-f38c8e39cac7': Path(
                '04 Lab 3-1 Basic MSP430 Assembly from Roots in LC-3/'
                'index.cnxml'),
            'f362376d-f032-481a-b848-5047ede49372': Path(
                '10 Helpful General Information/'
                '01 MSP430 LaunchPad Test Circuit Breadboarding Instructions/'
                'index.cnxml'),
            '21b817d8-fcd5-4d57-9c93-0faad87d51bf': Path(
                '10 Helpful General Information/'
                '02 A Student to Student Intro to IDE '
                'Programming and CCS4/index.cnxml'),
            '5f50d5b5-ccef-4fd0-959b-2fa90bf01a53': Path(
                '06 Lab 4-1 Interrupt Driven Programming in MSP430 Assembly/'
                'index.cnxml'),
            '8c0df5d8-92b1-4607-8435-a9e6046dfbdf': Path(
                '08 Lab 5-1 C Language Programming through the ADC '
                'and the MSP430/index.cnxml'),
            'e537c09a-406c-47a7-bfc8-fc34ff9c878b': Path(
                '05 Lab 3-2 Digital Input and Output with the MSP430/'
                'index.cnxml'),
            '29ea6719-4936-419b-9195-6da12e47b417': Path(
                '07 Lab 4-2 Putting It All Together/index.cnxml'),
            '28af42a0-2770-46ab-8411-ca00335d6cdc': Path(
                '09 Lab 5-2 Using C and the ADC for "Real World" '
                'Applications with the MSP430/index.cnxml'),
            '67f54f99-2599-4cbb-b226-4eee7ef80cde': Path(
                '02 A Quartus Project from Start to Finish∶ '
                '2 Bit Mux Tutorial/index.cnxml'),
            '077dba20-bbf5-4cf4-9f3c-a6eb0d6c17eb': Path(
                '01 Introduction to Quartus and Circuit Diagram Design/'
                'index.cnxml'),
            '57918948-050d-45a8-bfea-1c894cc312ee': Path(
                '03 Lab 1-1∶ 4-Bit Mux and all NAND∕NOR Mux/index.cnxml'),
        }
        results = self.make_results_relative(uuid_to_path_mapping, loc)
        assert results == expected
