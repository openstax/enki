import re
from functools import partial

from lxml import etree


__all__ = (
    'NSMAP',
    'make_cnx_xpath',
    'parse_metadata',
)


# XML namespace mapping used by lxml.etree for parsing and element lookup
NSMAP = {
    "bib": "http://bibtexml.sf.net/",
    "c": "http://cnx.rice.edu/cnxml",
    "cnxorg": "http://cnx.rice.edu/system-info",
    "col": "http://cnx.rice.edu/collxml",
    "data": "http://www.w3.org/TR/html5/dom.html#custom-data-attribute",
    "datadev": "http://dev.w3.org/html5/spec/#custom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "epub": "http://www.idpf.org/2007/ops",
    "lrmi": "http://lrmi.net/the-specification",
    "m": "http://www.w3.org/1998/Math/MathML",
    "md": "http://cnx.rice.edu/mdml",
    "mod": "http://cnx.rice.edu/#moduleIds",
    "qml": "http://cnx.rice.edu/qml/1.0",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}


LICENSE_INFO_MAP = {
    'by': {
        'text': 'Creative Commons Attribution License',
        'versions': ['1.0', '2.0', '3.0', '4.0']
    },
    'by-nd': {
        'text': 'Creative Commons Attribution-NoDerivs License',
        'versions': ['1.0', '2.0']
    },
    'by-nd-nc': {
        'text': 'Creative Commons Attribution-NoDerivs-NonCommercial' +
                ' License',
        # TODO: by-nd-nc version 1.0 does not exist, remove when we
        #       know it is safe
        'versions': ['1.0', '2.0']
    },
    'by-sa': {
        'text': 'Creative Commons Attribution-ShareAlike License',
        'versions': ['1.0', '2.0']
    },
    'by-nc': {
        'text': 'Creative Commons Attribution-NonCommercial License',
        'versions': ['1.0', '2.0']
    },
    'by-nc-sa': {
        'text': 'Creative Commons Attribution-NonCommercial-ShareAlike' +
                ' License',
        'versions': ['4.0']
    }
}


def _maybe(vals):
    """Grab the first value if it exists."""
    try:
        return vals[0]
    except IndexError:
        return None


def make_cnx_xpath(elm_tree):
    """Makes an xpath function that includes the CNX namespaces.

    :param elm_tree: the xml element to begin the xpath from
    :type elm_tree: an element-like object from :mod:`lxml.etree`

    """
    return partial(elm_tree.xpath, namespaces=NSMAP)


def _squash_to_text(elm, remove_namespaces=False):
    if elm is None:  # pragma: no cover
        return None
    value = [elm.text or '']
    for child in elm.getchildren():
        value.append(etree.tostring(child).decode('utf-8').strip())
    if remove_namespaces:
        value = [re.sub(' xmlns:?[^=]*="[^"]*"', '', v) for v in value]
    value = ''.join(value)
    return value


def _parse_license_url(url):
    is_localized = '/deed.' in url
    if is_localized:
        deed_idx = url.rindex('/deed.')
        # language is after '/deed.'
        license_lang = url[deed_idx + 6:]
        type_and_version = url[:deed_idx].split('/')[-2:]
    else:
        type_and_version = url.rstrip('/').split('/')[-2:]
        license_lang = None
    if len(type_and_version) != 2 or 'creativecommons.org' not in url:
        raise Exception(f'Invalid license url: "{url}"')
    typ, ver = type_and_version
    # Even if the license is localized, it should have a valid type and
    # version in the url
    if (typ not in LICENSE_INFO_MAP or
            ver not in LICENSE_INFO_MAP[typ]['versions']):
        raise Exception('Unknown license type or version: ' +
                        f'{{ url: "{url}", type: "{typ}", version: "{ver}" }}')
    return (typ, ver, license_lang)


def _parse_license(license_el, language):
    url = None
    if license_el is not None:
        url = license_el.attrib.get('url', None)
        if url is not None:
            url = url.strip()
            if len(url) == 0:
                url = None
    if url is None:
        return (None, None)

    typ, ver, license_lang = _parse_license_url(url)
    if license_lang is not None and license_lang != 'en':
        # In this instance, use the text in the element. Hopefully this text
        # has been translated. We may store translated versions of license
        # text in LICENSE_INFO_MAP in the future.
        if language != license_lang:
            raise Exception(f'Language mismatch - md:license: {license_lang}, '
                            f'md:language: {language}')
        text = license_el.text
        if text is not None:
            text = text.strip()
            if len(text) == 0:
                text = None
        if text is None:
            raise Exception(f'Expected license text for "{url}"')
    else:
        text = LICENSE_INFO_MAP[typ]['text']
    return (text, url)


def parse_super_metadata(elm_tree):
    def _xpath(elem, query):
        return elem.xpath(query, namespaces=NSMAP)

    def _safe_strip(maybe_str):
        return None if maybe_str is None else maybe_str.strip()

    super_elm = _maybe(_xpath(elm_tree, '//md:super'))

    if super_elm is None:
        return None

    tags = [
        {
            k: v
            for k, v in (
                ("type", _safe_strip(elem.get("type"))),
                ("link", _safe_strip(elem.get("link"))),
                ("text", _safe_strip(elem.text))
            )
            if v
        }
        for elem in _xpath(super_elm, '//md:tags//md:tag')
    ]
    assert all(t.get("text", None) is not None for t in tags)
    subject_name = _safe_strip(
        _maybe(_xpath(super_elm, '//md:subject-name/text()'))
    )
    return {
        k: v for k, v in (
            ("subject_name", subject_name),
            ("tags", tags),
        )
        if v
    }


def parse_metadata(elm_tree):
    """Given an element-like object (:mod:`lxml.etree`)
    lookup the metadata and return the found elements

    :param elm_tree: the root xml element
    :type elm_tree: an element-like object from :mod:`lxml.etree`
    :returns: common metadata properties
    :rtype: dict

    """
    xpath = make_cnx_xpath(elm_tree)

    uuid = xpath('//md:uuid/text()')[0]
    version = _maybe(xpath('//md:version/text()'))
    language = _maybe(xpath('//md:language/text()'))
    license_text, license_url = _parse_license(
        _maybe(xpath('//md:license')), language)
    props = {
        'id': _maybe(xpath('//md:content-id/text()')),
        'uuid': uuid,
        'canonical_book_uuid': _maybe(
            xpath('//md:canonical-book-uuid/text()')
        ),
        'version': version,
        'revised': _maybe(xpath('//md:revised/text()')),
        'title': (
            ''.join(xpath('/c:document/c:title//text()')).strip() or
            xpath('//md:title/text()')[0]
        ),
        'slug': _maybe(xpath('//md:slug/text()')),
        'license_url': license_url,
        'license_text': license_text,
        'language': language,
        'abstract': _squash_to_text(
            _maybe(xpath('//md:abstract')),
            remove_namespaces=True,
        ),
        # cnx-archive-uri is used extensively in enki/bakery-src
        'cnx-archive-uri': f"{uuid}@{version or ''}",
        'super_metadata': parse_super_metadata(elm_tree)
    }
    return props
