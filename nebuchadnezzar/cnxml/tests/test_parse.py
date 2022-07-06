import pytest
from lxml import etree

from cnxml.parse import NSMAP, parse_metadata


@pytest.fixture
def xml(datadir):
    with (datadir / 'valid_collection.xml').open() as fb:
        xml = etree.parse(fb)
    return xml


@pytest.fixture
def git_xml(datadir):
    with (datadir / 'valid_git_collection.xml').open() as fb:
        xml = etree.parse(fb)
    return xml


def test_parse(xml):
    # Call the target
    props = parse_metadata(xml)

    expected_props = {
        'abstract': (
            'This introductory, algebra-based, two-semester college physics '
            'book is grounded with real-world examples, illustrations, and '
            'explanations to help students grasp key, fundamental physics '
            'concepts. This online, fully editable and customizable title '
            'includes learning objectives, concept questions, links to labs '
            'and simulations, and ample practice opportunities to solve '
            'traditional physics application problems.'
        ),
        'authors': ('OpenStaxCollege',),
        'created': '2012/01/23 13:03:30.293 US/Central',
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (
            'ac circuits',
            'atomic physics',
            'bioelectricity',
            'biological and medical applications',
            'circuits',
        ),
        'language': 'en',
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'license_text': 'Creative Commons Attribution License',
        'licensors': ('OSCRiceUniversity',),
        'maintainers': ('OpenStaxCollege', 'cnxcap'),
        'print_style': 'ccap-physics',
        'revised': '2015/07/27 12:55:32.442 GMT-5',
        'subjects': ('Mathematics and Statistics', 'Science and Technology'),
        'title': 'College Physics',
        'version': '1.9',
        'uuid': None,
        'canonical_book_uuid': None,
        'slug': None,
    }
    # Verify the metadata
    assert props == expected_props


def test_git_parse(git_xml):
    # Call the target
    props = parse_metadata(git_xml)

    expected_props = {
        'abstract': None,
        'authors': (),
        'created': None,
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (),
        'language': 'en',
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'license_text': 'Creative Commons Attribution License',
        'licensors': (),
        'maintainers': (),
        'print_style': None,
        'revised': None,
        'subjects': (),
        'title': 'College Physics',
        'version': None,
        'uuid': 'e1edc39a-14cd-4d61-886f-36bebd27e2d2',
        'canonical_book_uuid': None,
        'slug': 'college-physics'
    }
    # Verify the metadata
    assert props == expected_props


# https://github.com/Connexions/cnx-press/issues/17
def test_parse_without_abstract(xml):
    # Remove the abstract
    elm = xml.xpath('//md:abstract',
                    namespaces=NSMAP)[0]
    elm.getparent().remove(elm)

    # Call the target
    props = parse_metadata(xml)

    # Verify the abstract is empty
    assert props['abstract'] is None


def test_parse_with_cnxml_abstract(xml):
    abstract = '<list><item>A</item><item>C</item><item>E</item></list>'

    # Find and modify the abstract to include wrapping text
    elm = xml.xpath('//md:abstract', namespaces=NSMAP)[0]
    elm.text = "FOO "
    abstract_elms = etree.fromstring(abstract)
    abstract_elms.tail = " BAR"
    elm.append(abstract_elms)

    elm.tail = " BAR"

    # Call the target
    props = parse_metadata(xml)

    expected_abstract = 'FOO {} BAR'.format(abstract)
    # parse the metadata into a dict and check for the abstract.
    assert props['abstract'] == expected_abstract


def test_parse_derived_from(xml):
    uri = 'https://example.org/content/col12345/1.11'
    title = 'Foo Bar'

    derived_from = (
        '<derived-from xmlns="{}" url="{}">'
        '<title>{}</title>'
        '</derived-from>'
    ).format(NSMAP['md'], uri, title)

    # Find and modify the metadata
    elm = xml.xpath('//col:metadata', namespaces=NSMAP)[0]
    # Create md:derive-from element and md:title sub-element
    derived_from_elms = etree.fromstring(derived_from)
    elm.append(derived_from_elms)

    # Call the target
    props = parse_metadata(xml)

    # Verify properties
    expected = {
        'title': title,
        'uri': uri,
    }
    assert props['derived_from'] == expected
    # Verify we've discovered the correct title
    assert props['title'] == 'College Physics'


def test_parse_with_minimal_metadata():
    cnxml = """
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:abstract/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    expected_props = {
        'abstract': '',
        'authors': (),
        'created': None,
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (),
        'language': None,
        'license_url': None,
        'license_text': None,
        'licensors': (),
        'maintainers': (),
        'print_style': None,
        'revised': None,
        'subjects': (),
        'title': 'College Physics',
        'version': None,
        'uuid': None,
        'canonical_book_uuid': None,
        'slug': None,
    }
    # Verify the metadata
    assert props == expected_props


def test_parse_with_optional_metadata():
    cnxml = """
        <document xmlns="http://cnx.rice.edu/cnxml">
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:title>College Physics</md:title>
                <md:abstract/>
                <md:uuid>e1edc39a-14cd-4d61-886f-36bebd27e2d2</md:uuid>
                <md:canonical-book-uuid>70fe3889-8d4b-4061-8efa-d00c655f474d</md:canonical-book-uuid>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    expected_props = {
        'abstract': '',
        'authors': (),
        'created': None,
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (),
        'language': None,
        'license_url': None,
        'license_text': None,
        'licensors': (),
        'maintainers': (),
        'print_style': None,
        'revised': None,
        'subjects': (),
        'title': 'College Physics',
        'version': None,
        'uuid': 'e1edc39a-14cd-4d61-886f-36bebd27e2d2',
        'canonical_book_uuid': '70fe3889-8d4b-4061-8efa-d00c655f474d',
        'slug': None,
    }
    # Verify the metadata
    assert props == expected_props


@pytest.mark.parametrize(
    'license_el',
    [
        '<md:license url=""/>',
        '<md:license url="  "/>',
        '<md:license/>',
        ''
    ]
)
def test_parse_no_license_url_returns_default(license_el):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:abstract/>
                {license_el}
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    expected_props = {
        'abstract': '',
        'authors': (),
        'created': None,
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (),
        'language': None,
        'license_url': None,
        'license_text': None,
        'licensors': (),
        'maintainers': (),
        'print_style': None,
        'revised': None,
        'subjects': (),
        'title': 'College Physics',
        'version': None,
        'uuid': None,
        'canonical_book_uuid': None,
        'slug': None,
    }
    # Verify the metadata
    assert props == expected_props


# Currently, the en license is used in many instances where md:language is not en
@pytest.mark.parametrize(
    'license_url,license_text,md_lang',
    [
        (
            'http://creativecommons.org/licenses/by/4.0/deed.en',
            'Creative Commons Attribution License',
            'en'
        ),
        (
            # https should work too
            'https://creativecommons.org/licenses/by/4.0/deed.en',
            'Creative Commons Attribution License',
            'en'
        ),
        (
            'https://creativecommons.org/licenses/by/4.0',
            'Creative Commons Attribution License',
            'en'
        ),
        (
            'http://creativecommons.org/licenses/by/2.0/',
            'Creative Commons Attribution License',
            'pl'
        ),
        (
            'http://creativecommons.org/licenses/by-nd/2.0/',
            'Creative Commons Attribution-NoDerivs License',
            'es'
        ),
        (
            # Spaces should be ignored
            ' http://creativecommons.org/licenses/by-nc-sa/4.0/ ',
            'Creative Commons Attribution-NonCommercial-ShareAlike License',
            'en'
        )
    ]
)
def test_parse_license_url_returns_expected_value(license_url, license_text, md_lang):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:abstract/>
                <md:language>{md_lang}</md:language>
                <md:license url="{license_url}"/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    expected_props = {
        'abstract': '',
        'authors': (),
        'created': None,
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (),
        'language': md_lang,
        'license_url': license_url.strip(),
        'license_text': license_text,
        'licensors': (),
        'maintainers': (),
        'print_style': None,
        'revised': None,
        'subjects': (),
        'title': 'College Physics',
        'version': None,
        'uuid': None,
        'canonical_book_uuid': None,
        'slug': None,
    }
    # Verify the metadata
    assert props == expected_props


# For now, only check localized license match their language
@pytest.mark.parametrize(
    'license_el,md_lang',
    [
        ('<md:license url="creativecommons.org/licenses/by/4.0/deed.pl">   </md:license>', 'xx'),
        ('<md:license url="creativecommons.org/licenses/by/4.0/deed.pl"/>', 'xx')
    ]
)
def test_parse_license_with_localized_url_and_lang_mismatch_should_error(license_el, md_lang):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:language>{md_lang}</md:language>
                <md:abstract/>
                {license_el}
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)

    with pytest.raises(Exception) as e:
        _ = parse_metadata(xml)
    assert 'Language mismatch' in str(e)


@pytest.mark.parametrize(
    'license_url,license_text,md_lang',
    [
        (
            'https://creativecommons.org/licenses/by/4.0/deed.could_be_anything',
            'The part after \'/deed.\' in the url is not consistent',
            'could_be_anything'
        ),
        (
            'https://creativecommons.org/licenses/by/4.0/deed.pl',
            'Uznanie autorstwa (CC BY)',
            'pl'
        ),
        (
            ' https://creativecommons.org/licenses/by/4.0/deed.xx ',
            ' Spaces in url and text should be removed ',
            'xx'
        )
    ]
)
def test_parse_localized_license_url_returns_element_text(license_url, license_text, md_lang):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:abstract/>
                <md:language>{md_lang}</md:language>
                <md:license url="{license_url}"> {license_text} </md:license>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    expected_props = {
        'abstract': '',
        'authors': (),
        'created': None,
        'derived_from': {'title': None, 'uri': None},
        'id': 'col11406',
        'keywords': (),
        'language': md_lang,
        'license_url': license_url.strip(),
        'license_text': license_text.strip(),
        'licensors': (),
        'maintainers': (),
        'print_style': None,
        'revised': None,
        'subjects': (),
        'title': 'College Physics',
        'version': None,
        'uuid': None,
        'canonical_book_uuid': None,
        'slug': None,
    }
    # Verify the metadata
    assert props == expected_props


@pytest.mark.parametrize(
    'license_el',
    [
        '<md:license url="creativecommons.org/licenses/by/4.0/deed.xx">   </md:license>',
        '<md:license url="creativecommons.org/licenses/by/4.0/deed.xx"/>'
    ]
)
def test_parse_localized_license_with_no_license_text_should_error(license_el):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:language>xx</md:language>
                <md:abstract/>
                {license_el}
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)

    with pytest.raises(Exception) as e:
        _ = parse_metadata(xml)
    assert 'Expected license text for' in str(e)


@pytest.mark.parametrize(
    'license_url',
    [
        # Bad type
        'https://creativecommons.org/licenses/by-sad/4.0/deed.xx',
        # Bad type
        'https://creativecommons.org/licenses/by-something-else/4.0/',
        # Bad version
        'https://creativecommons.org/licenses/by/999.0/'
    ]
)
def test_parse_license_url_with_typo_should_error(license_url):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:abstract/>
                <md:license url="{license_url}"/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)

    with pytest.raises(Exception) as e:
        _ = parse_metadata(xml)
    assert 'Unknown license type or version' in str(e)


@pytest.mark.parametrize(
    'license_url',
    [
        'this-is-a-bad-url',
        '/deed.xx',
        'deed.xx',
        # Valid, but not a license url
        'http://www.example.com/by/4.0/',
        # Bad
        'a/b/c/d/e/f/g'
    ]
)
def test_parse_license_with_bad_url_should_error(license_url):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:abstract/>
                <md:license url="{license_url}"/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)

    with pytest.raises(Exception) as e:
        _ = parse_metadata(xml)
    assert 'Invalid license url' in str(e)
