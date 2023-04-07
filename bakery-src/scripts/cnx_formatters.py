# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import logging
import sys

from .cnx_models import utf8

from lxml import etree
from .profiler import timed


logger = logging.getLogger('cnxepub')

IS_PY3 = sys.version_info.major == 3


__all__ = (
    'DocumentContentFormatter'
)


class DocumentContentFormatter(object):
    def __init__(self, document):
        self.document = document

    def __unicode__(self):
        return self.__bytes__().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        html = """\
<html xmlns="http://www.w3.org/1999/xhtml">
  {}
</html>""".format(utf8(self.document.content))
        html = _fix_namespaces(html.encode('utf-8'))
        et = etree.HTML(html.decode('utf-8'))
        return etree.tostring(et, pretty_print=True, encoding='utf-8')

@timed
def _fix_namespaces(html):
    # Get rid of unused namespaces and put them all in the root tag
    nsmap = {None: u"http://www.w3.org/1999/xhtml",
             u"m": u"http://www.w3.org/1998/Math/MathML",
             u"epub": u"http://www.idpf.org/2007/ops",
             u"rdf": u"http://www.w3.org/1999/02/22-rdf-syntax-ns#",
             u"dc": u"http://purl.org/dc/elements/1.1/",
             u"lrmi": u"http://lrmi.net/the-specification",
             u"bib": u"http://bibtexml.sf.net/",
             u"data":
                 u"http://www.w3.org/TR/html5/dom.html#custom-data-attribute",
             u"qml": u"http://cnx.rice.edu/qml/1.0",
             u"datadev": u"http://dev.w3.org/html5/spec/#custom",
             u"mod": u"http://cnx.rice.edu/#moduleIds",
             u"md": u"http://cnx.rice.edu/mdml",
             u"c": u"http://cnx.rice.edu/cnxml"
             }
    root = etree.fromstring(html)

    # lxml has a built in function to do this without destroying comments
    etree.cleanup_namespaces(root, top_nsmap=nsmap)

    return etree.tostring(root, pretty_print=True, encoding='utf-8')

# /YANK
