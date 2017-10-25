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

# XXX (2017-10-12) deps-on-cnx-archive: Depends on cnx-archive
from cnxarchive.config import TEST_DATA_DIRECTORY


class BaseTestCase(object):

    @property
    def target(self):
        raise NotImplementedError()

    def call_target(self, *args, **kwargs):
        return self.target(*args, **kwargs)

    def get_file(self, filename):
        path = os.path.join(TEST_DATA_DIRECTORY, filename)
        with open(path, 'r') as fp:
            return fp.read()


class TestCnxml2Html(BaseTestCase):

    @property
    def target(self):
        from cnxdb.triggers.transforms.converters import cnxml_to_full_html
        return cnxml_to_full_html

    def test_dev_ctoh_version(self):
        import rhaptos.cnxmlutils
        # Mimic the in-database environment: no path
        os.environ['PATH'] = ''
        reload(rhaptos.cnxmlutils)
        cnxml = self.get_file('m42033-1.3.cnxml')
        content = self.call_target(cnxml)

        assert '0+unknown' not in content

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        cnxml = self.get_file('m42033-1.3.cnxml')

        content = self.call_target(cnxml)

        assert '<html' in content
        assert '<body' in content

        # Check for ctoh version
        import rhaptos.cnxmlutils
        assert rhaptos.cnxmlutils.__version__ in content

    # FIXME This test belongs in rhaptos.cnxmlutils
    def test_module_transform_image_with_print_width(self):
        cnxml = self.get_file('m31947-1.3.cnxml')

        content = self.call_target(cnxml)

        # Assert <img> tag is generated
        img = re.search('(<img [^>]*>)', content)
        assert img is not None
        img = img.group(1)
        assert 'src="graphics1.jpg"' in img
        assert 'data-print-width="6.5in"' in img


class TestHtml2Cnxml(BaseTestCase):

    @property
    def target(self):
        from cnxdb.triggers.transforms.converters import html_to_full_cnxml
        return html_to_full_cnxml

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        html = self.get_file('m42033-1.3.html')

        content = self.call_target(html)

        # Check for partial conversion.
        # rhaptos.cnxmlutils has tests to ensure full conversion.
        assert b'<document' in content
