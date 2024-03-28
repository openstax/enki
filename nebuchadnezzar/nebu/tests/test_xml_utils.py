# -*- coding: utf-8 -*-
import sys
import unittest

from lxml import etree
from nebu.xml_utils import etree_from_str, fix_namespaces, squash_xml_to_text

import pytest

IS_PY2 = sys.version_info.major == 2


class TestSquashXMLToText(unittest.TestCase):

    content = (
        '<div data-type="description" xmlns="http://www.w3.org/1999/xhtml">'
        'FOO '
        '<p><math xmlns="http://www.w3.org/1998/Math/MathML"/></p>'
        '<p><math xmlns="http://www.w3.org/1998/Math/MathML"/></p>'
        ' BAR'
        '</div>'
    )

    parser = etree.XMLParser(resolve_entities=True, encoding='ascii')

    def setUp(self):
        self.content = etree.fromstring(self.content, self.parser)

    @property
    def target(self):
        return squash_xml_to_text

    def test(self):
        result = self.target(self.content, False)

        expected = (
            'FOO '
            '<p xmlns="http://www.w3.org/1999/xhtml">'
            '<math xmlns="http://www.w3.org/1998/Math/MathML"/></p>'
            '<p xmlns="http://www.w3.org/1999/xhtml">'
            '<math xmlns="http://www.w3.org/1998/Math/MathML"/></p>'
            ' BAR'
        )
        assert result == expected

    def test_with_namespace_removal(self):
        result = self.target(self.content, True)

        expected = 'FOO <p><math/></p><p><math/></p> BAR'
        assert result == expected

    def test_text_only(self):
        txt = '<div>Hello Wórld!</div>'
        expected = 'Hello Wórld!'
        if IS_PY2:
            txt = txt.decode('utf-8')
            expected = expected.decode('utf-8')

        result = self.target(etree.fromstring(txt, self.parser), True)
        assert result == expected

    def test_single_elem_only(self):
        txt = '<div><span>Hello Wórld!</span></div>'
        expected = '<span>Hello Wórld!</span>'
        if IS_PY2:
            txt = txt.decode('utf-8')
            expected = expected.decode('utf-8')

        result = self.target(etree.fromstring(txt), True)
        assert result == expected

    def test_with_leading_whitespace(self):
        txt = '\n  <div>\n  <span>Hello Wórld!</span>  </div>'
        expected = '<span>Hello Wórld!</span>'
        if IS_PY2:
            txt = txt.decode('utf-8')
            expected = expected.decode('utf-8')

        result = self.target(etree.fromstring(txt), True)
        assert result == expected

    def test_with_space_separated_elements(self):
        txt = (
            '<div>'
            'count '
            '<span>1</span>'
            '<span>,</span> '
            '<span>2</span>'
            '<span>,</span> '
            '... '
            '<span>10</span> '
            'stop!'
            '</div>'
        )
        result = self.target(etree.fromstring(txt), True)

        expected = (
            'count <span>1</span><span>,</span> <span>2</span>'
            '<span>,</span> ... <span>10</span> stop!'
        )
        assert result == expected

    def test_with_buffered_utf8_text(self):
        txt = (
            '<div>'
            'Ottó '
            '<span>vs</span>'
            ' Hélène'
            '</div>'
        )
        expected = 'Ottó <span>vs</span> Hélène'
        if IS_PY2:
            txt = txt.decode('utf-8')
            expected = expected.decode('utf-8')

        result = self.target(etree.fromstring(txt), True)
        assert result == expected


def test_fixnamespaces(snapshot):
    before = etree_from_str(
        """\
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
    <body xmlns:bib="http://bibtexml.sf.net/">
        <p>Some text<em><!-- no-selfclose --></em>!</p>
        <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mtext>H</mtext>
        </math>
        <div>
            <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mtext>More deeply nested</mtext>
            </math>
        </div>
        <div xmlns:epub="http://www.idpf.org/2007/ops">
            <aside role="doc-footnote" epub:type="footnote">
                Something goes inside here
            </aside>
        </div>
    </body>
</html>"""
    )

    snapshot.assert_match(fix_namespaces(before).decode(), "after.xml")


@pytest.mark.parametrize(
    "xml_doc,type",
    [
        (
            b'\xef\xbb\xbf<?xml version="1.0"?>\n<a><b></b></a>',
            "bom without encoding"
        ),
        (
            b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>\n<a><b></b></a>',
            "bom with encoding"
        ),
        (
            b'<?xml version="1.0" encoding="utf-8"?>\n<a><b></b></a>',
            "no bom"
        ),
        (
            b'<?xml version="1.0"?>\n<a><b></b></a>',
            "no encoding"
        ),
        (
            b'<?xml version="1.0" encoding="ascii"?>\n<a><b></b></a>',
            "ascii encoding"
        ),
    ]
)
def test_fromstring(xml_doc, type):
    tree = etree_from_str(xml_doc)
    assert len(tree) > 0, f"{type}: failed to parse"
    assert len(tree.xpath('//a')) > 0, f"{type}: bad parsing result"
