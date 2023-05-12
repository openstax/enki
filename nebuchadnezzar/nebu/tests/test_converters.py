# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014-2017, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys

from nebu.converters import (
    cnxml_abstract_to_html,
    etree_cnxml_to_full_html,
)
from nebu.xml_utils import open_xml


HERE = os.path.abspath(os.path.dirname(__file__))


class TestCnxml2Html:

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        cnxml = open_xml(os.path.join(HERE, 'm42033-1.3.cnxml'))

        content = etree_cnxml_to_full_html(cnxml)

        assert '<html' in content
        assert '<body' in content


def test_cnxml_abstract_to_html():
    abstract = (
        "In this section you will:<list><item>A</item><item>B</item>"
        "<item><m:math><m:mi>x</m:mi></m:math></item>"
        "<item><m:math><m:mi>y</m:mi></m:math></item></list>"
    )

    # Call the target
    converted_abstract = cnxml_abstract_to_html(abstract)

    with open(os.path.join(HERE, 'm51252-abstract.snippet.html'), 'r') as fb:
        expected_abstract = fb.read().strip()
    if sys.version_info >= (3,):
        expected_abstract = expected_abstract.encode('utf-8')

    assert converted_abstract == expected_abstract


def test_diffs(snapshot):
    conversions = [
        'cite',
        'classed',
        'code',
        'definition',
        'div_span_not_self_closing',
        'emphasis',
        'exercise-injected',
        'figure',
        'footnote',
        'glossary',
        'img-longdesc',
        'label',
        'lang',
        'link',
        'list',
        'math_problem_m65735',
        'media',
        'newline',
        'note',
        'para',
        'problem_m58457_1.6.self_closing',
        'table',
        'term-and-link',
        'title',
        'xhtml-characters',
    ]
    for t in conversions:
        cnxml = open_xml(os.path.join(HERE, "cnxml", f"{t}.cnxml"))
        html = etree_cnxml_to_full_html(cnxml)
        snapshot.assert_match(html, f'{t}.xhtml')
