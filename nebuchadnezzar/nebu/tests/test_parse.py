import json

import pytest
from lxml import etree

from nebu.parse import parse_metadata


@pytest.fixture
def git_xml(datadir):
    with (datadir / 'valid_git_collection.xml').open() as fb:
        xml = etree.parse(fb)
    return xml


def assert_props_match(snapshot, props, snapshot_name="metadata.json"):
    snapshot.assert_match(json.dumps(props, indent=2), snapshot_name)


def test_git_parse(git_xml, snapshot):
    # Call the target
    props = parse_metadata(git_xml)
    assert_props_match(snapshot, props)


def test_parse_with_minimal_metadata(snapshot):
    cnxml = """
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:uuid>e1edc39a-14cd-4d61-886f-36bebd27ebee</md:uuid>
                <md:abstract/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    assert_props_match(snapshot, props)


def test_parse_with_optional_metadata(snapshot):
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

    assert_props_match(snapshot, props)


@pytest.mark.parametrize(
    'license_el',
    [
        '<md:license url=""/>',
        '<md:license url="  "/>',
        '<md:license/>',
        ''
    ]
)
def test_parse_no_license_url_returns_default(license_el, snapshot):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
                <md:abstract/>
                {license_el}
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    assert_props_match(snapshot, props)


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
def test_parse_license_url_returns_expected_value(license_url, license_text, md_lang, snapshot):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
                <md:abstract/>
                <md:language>{md_lang}</md:language>
                <md:license url="{license_url}"/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    assert_props_match(snapshot, props)


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
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
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
def test_parse_localized_license_url_returns_element_text(license_url, license_text, md_lang, snapshot):
    cnxml = f"""
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>College Physics</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
                <md:abstract/>
                <md:language>{md_lang}</md:language>
                <md:license url="{license_url}"> {license_text} </md:license>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    assert_props_match(snapshot, props)


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
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
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
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
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
                <md:uuid>e1edc39a-14cd-4d61-886f-deadbee7e2d2</md:uuid>
                <md:abstract/>
                <md:license url="{license_url}"/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)

    with pytest.raises(Exception) as e:
        _ = parse_metadata(xml)
    assert 'Invalid license url' in str(e)


def test_parse_no_title():
    cnxml = """
        <document xmlns="http://cnx.rice.edu/cnxml">
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:uuid>e1edc39a-14cd-4d61-886f-36bebd27ebee</md:uuid>
                <md:abstract/>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)

    with pytest.raises(IndexError):
        _ = parse_metadata(xml)


def test_parse_super_metadata(snapshot):
    cnxml = """
        <document xmlns="http://cnx.rice.edu/cnxml">
            <title>something</title>
            <metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">
                <md:content-id>col11406</md:content-id>
                <md:uuid>e1edc39a-14cd-4d61-886f-36bebd27ebee</md:uuid>
                <md:super>
                    <md:subject-name>Subject Name</md:subject-name>
                    <md:tags>
                        <md:tag type="preparedness">A tag</md:tag>
                        <md:tag type="practice">B tag</md:tag>
                        <md:tag type="practice" link="https://...">C tag</md:tag>
                    </md:tags>
                </md:super>
            </metadata>
        </document>
    """

    xml = etree.fromstring(cnxml)
    props = parse_metadata(xml)

    assert_props_match(snapshot, props)
