# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""CNXML <-> HTML conversion code."""

import os
import sys
from io import BytesIO
try:
    from importlib import reload
except ImportError:
    pass  # reload() is a built-in global in py2

import rhaptos.cnxmlutils
from lxml import etree

__all__ = (
    'DEFAULT_XMLPARSER', 'ensure_bytes',
    'cnxml_abstract_to_html',
    'cnxml_to_html', 'cnxml_to_full_html',
    'html_to_cnxml', 'html_to_full_cnxml',
)

here = os.path.abspath(os.path.dirname(__file__))
LOCAL_XSL_DIR = os.path.abspath(os.path.join(here, 'xsl'))
RHAPTOS_CNXMLUTILS_DIR = os.path.dirname(rhaptos.cnxmlutils.__file__)

XSL_DIR = os.path.abspath(os.path.join(RHAPTOS_CNXMLUTILS_DIR, 'xsl'))
MATHML_XSL_PATH = os.path.abspath(os.path.join(
    LOCAL_XSL_DIR, 'content2presentation.xsl'))


def _gen_xsl(f, d=XSL_DIR):
    transform = etree.XSLT(etree.parse(os.path.join(d, f)))

    def transform_w_version(*args, **kwargs):
        # If git is not in $PATH, rhaptos.cnxmlutils.__version__ returns
        # "0+unknown"
        if '/usr/bin' not in os.getenv('PATH', ''):
            os.environ['PATH'] = '/usr/bin:{}'.format(os.environ['PATH'])
            reload(rhaptos.cnxmlutils)
        kwargs['version'] = etree.XSLT.strparam(
            rhaptos.cnxmlutils.__version__)
        return transform(*args, **kwargs)

    return transform_w_version


CNXML_TO_HTML_XSL = _gen_xsl('cnxml-to-html5.xsl')
CNXML_TO_HTML_METADATA_XSL = _gen_xsl('cnxml-to-html5-metadata.xsl')
HTML_TO_CNXML_XSL = _gen_xsl('html5-to-cnxml.xsl')
MATHML_XSL = _gen_xsl(MATHML_XSL_PATH, '.')

XML_PARSER_OPTIONS = {
    'load_dtd': True,
    'resolve_entities': True,
    'no_network': False,   # don't force loading our cnxml/DTD packages
    'attribute_defaults': False,
}
DEFAULT_XMLPARSER = etree.XMLParser(**XML_PARSER_OPTIONS)


# ############### #
#   CNXML->HTML   #
# ############### #

HTML_TEMPLATE_FOR_CNXML = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
{metadata}
{content}
</html>
"""


def _transform_cnxml_to_html_body(xml):
    """Transform the cnxml XML (``etree.ElementTree``) content body to html."""
    # Tranform content MathML to presentation MathML so MathJax can display it
    xml = MATHML_XSL(xml)
    return CNXML_TO_HTML_XSL(xml)


def _transform_cnxml_to_html_metadata(xml):
    """Transform the cnxml XML (``etree.ElementTree``) metadata to html."""
    return CNXML_TO_HTML_METADATA_XSL(xml)


def ensure_bytes(text):
    if sys.version_info > (3,) and isinstance(text, str):
        text = text.encode('utf-8')
    return text


def cnxml_to_html(cnxml, xml_parser=DEFAULT_XMLPARSER):
    """Transform raw cnxml content to html (body content only)."""
    if not isinstance(cnxml, (etree._ElementTree, etree._Element,)):
        cnxml = etree.parse(BytesIO(ensure_bytes(cnxml)), xml_parser)

    # Transform the content to html.
    content = _transform_cnxml_to_html_body(cnxml)
    return str(content)


def cnxml_to_full_html(cnxml, xml_parser=DEFAULT_XMLPARSER):
    """Transform raw cnxml content to a full html."""
    if not isinstance(cnxml, (etree._ElementTree, etree._Element,)):
        cnxml = etree.parse(BytesIO(ensure_bytes(cnxml)), xml_parser)

    # Transform the content to html.
    content = cnxml_to_html(cnxml)
    # Transform the metadata to html.
    metadata = _transform_cnxml_to_html_metadata(cnxml)

    html = HTML_TEMPLATE_FOR_CNXML.format(metadata=metadata, content=content)
    return html


def cnxml_abstract_to_html(abstract):
    abstract = (
        '<document xmlns="http://cnx.rice.edu/cnxml" '
        'xmlns:m="http://www.w3.org/1998/Math/MathML" '
        'xmlns:md="http://cnx.rice.edu/mdml/0.4" '
        'xmlns:bib="http://bibtexml.sf.net/" '
        'xmlns:q="http://cnx.rice.edu/qml/1.0" '
        'cnxml-version="0.7"><content>{}</content></document>'
    ).format(abstract)
    # Does it have a wrapping tag?
    abstract_html = ensure_bytes(cnxml_to_html(abstract))

    # Rename the containing element, because the abstract is a snippet,
    #   not a document.
    abstract_html = etree.parse(BytesIO(abstract_html), DEFAULT_XMLPARSER)
    container = abstract_html.xpath('/*')[0]  # a 'body' tag.
    container.tag = 'div'

    return etree.tostring(abstract_html)


# ############### #
#   HTML->CNXML   #
# ############### #


def html_to_cnxml(html, xml_parser=DEFAULT_XMLPARSER):
    """Transform html content to cnxml."""
    if not isinstance(html, (etree._ElementTree, etree._Element,)):
        html = etree.parse(BytesIO(ensure_bytes(html)), xml_parser).getroot()
    elif isinstance(html, etree._ElementTree):
        html = html.getroot()

    # Do the namespace dance...
    nsmap = html.nsmap.copy()
    nsmap['h'] = nsmap.pop(None)

    # The transform only works when the root tag is 'body'.
    if html.xpath('/h:html', namespaces=nsmap):
        html = html.xpath('/h:html/h:body', namespaces=nsmap)[0]

    # Transform the content.
    cnxml = HTML_TO_CNXML_XSL(html)
    return etree.tostring(cnxml)


# FFF (18-Jan-2015) Forward compatible version of html_to_cnxml.
#     The forseable future shows a conversion that doesn't rely on legacy
#     to fill in the metadata for us. (FYI, legacy currently produces an
#     exported version of the cnxml that contains all the metadata
#     which it acquires from the database.
html_to_full_cnxml = html_to_cnxml
