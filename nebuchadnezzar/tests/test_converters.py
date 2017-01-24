# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import re
import unittest

# XXX (2017-10-12) deps-on-cnx-archive: Depends on cnx-archive
from cnxarchive.config import TEST_DATA_DIRECTORY


class Cnxml2HtmlTests(unittest.TestCase):

    maxDiff = None

    @property
    def target(self):
        from cnxdb.triggers.transforms.converters import cnxml_to_full_html
        return cnxml_to_full_html

    def call_target(self, *args, **kwargs):
        return self.target(*args, **kwargs)

    def get_file(self, filename):
        path = os.path.join(TEST_DATA_DIRECTORY, filename)
        with open(path, 'r') as fp:
            return fp.read()

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        cnxml = self.get_file('m42033-1.3.cnxml')
        html = self.get_file('m42033-1.3.html')

        content = self.call_target(cnxml)

        self.assertIn('<html', content)
        self.assertIn('<body', content)

    @unittest.skip("the DTD files are not externally available")
    def test_module_transform_entity_expansion(self):
        # Case to test that a document's internal entities have been
        #   deref'ed from the DTD and expanded
        cnxml = self.get_file('m10761-2.3.cnxml')

        content = self.call_target(cnxml)

        # &#995; is expansion of &lambda;
        self.assertTrue(content.find('&#955;') >= 0)

    # FIXME This test belongs in rhaptos.cnxmlutils
    def test_module_transform_image_with_print_width(self):
        cnxml = self.get_file('m31947-1.3.cnxml')

        content = self.call_target(cnxml)

        # Assert <img> tag is generated
        img = re.search('(<img [^>]*>)', content)
        self.assertTrue(img is not None)
        img = img.group(1)
        self.assertTrue('src="graphics1.jpg"' in img)
        self.assertTrue('data-print-width="6.5in"' in img)


class Html2CnxmlTests(unittest.TestCase):

    maxDiff = None

    @property
    def target(self):
        from cnxdb.triggers.transforms.converters import html_to_full_cnxml
        return html_to_full_cnxml

    def call_target(self, *args, **kwargs):
        return self.target(*args, **kwargs)

    def get_file(self, filename):
        path = os.path.join(TEST_DATA_DIRECTORY, filename)
        with open(path, 'r') as fp:
            return fp.read()

    def test_success(self):
        # Case to test the transformation of cnxml to html.
        html = self.get_file('m42033-1.3.html')

        content = self.call_target(html)

        # Check for partial conversion.
        # rhaptos.cnxmlutils has tests to ensure full conversion.
        self.assertIn('<document', content)
