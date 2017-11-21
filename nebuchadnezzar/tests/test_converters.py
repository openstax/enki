# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014-2017, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import re
try:
    from importlib import reload
except ImportError:
    pass  # reload() is a built-in global in py2

from cnxdb.triggers.transforms.converters import (
    cnxml_to_full_html,
    html_to_full_cnxml,
)


class BaseTestCase(object):

    def get_file(self, filename):
        here = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(here, filename)
        with open(path, 'r') as fp:
            return fp.read()


class TestCnxml2Html(BaseTestCase):

    def test_dev_ctoh_version(self):
        import rhaptos.cnxmlutils
        # Mimic the in-database environment: no path
        os.environ['PATH'] = ''
        reload(rhaptos.cnxmlutils)
        cnxml = self.get_file('m42033-1.3.cnxml')
        content = cnxml_to_full_html(cnxml)

        assert '0+unknown' not in content

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        cnxml = self.get_file('m42033-1.3.cnxml')

        content = cnxml_to_full_html(cnxml)

        assert '<html' in content
        assert '<body' in content

        # Check for ctoh version
        import rhaptos.cnxmlutils
        assert rhaptos.cnxmlutils.__version__ in content

    # FIXME This test belongs in rhaptos.cnxmlutils
    def test_module_transform_image_with_print_width(self):
        cnxml = self.get_file('m31947-1.3.cnxml')

        content = cnxml_to_full_html(cnxml)

        # Assert <img> tag is generated
        img = re.search('(<img [^>]*>)', content)
        assert img is not None
        img = img.group(1)
        assert 'src="graphics1.jpg"' in img
        assert 'data-print-width="6.5in"' in img


class TestHtml2Cnxml(BaseTestCase):

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        html = self.get_file('m42033-1.3.html')

        content = html_to_full_cnxml(html)

        # Check for partial conversion.
        # rhaptos.cnxmlutils has tests to ensure full conversion.
        assert b'<document' in content
