import base64
import logging
import re
import uuid
from lxml import etree, html
from .cnx_models import (Binder, content_to_etree, etree_to_content,
                         Document, CompositeDocument, flatten_to_documents)
from .profiler import timed

TRANSLUCENT_BINDER_ID = 'subcol'

HTML_DOCUMENT_NAMESPACES = {
    'xhtml': "http://www.w3.org/1999/xhtml",
    'epub': "http://www.idpf.org/2007/ops",
}


@timed
def squash_xml_to_text(elm, remove_namespaces=False):
    """Squash the given XML element (as `elm`) to a text containing XML.
    The outer most element/tag will be removed, but inner elements will
    remain. If `remove_namespaces` is specified, XML namespace declarations
    will be removed from the text.
    :param elm: XML element
    :type elm: :class:`xml.etree.ElementTree`
    :param remove_namespaces: flag to indicate the removal of XML namespaces
    :type remove_namespaces: bool
    :return: the inner text and elements of the given XML element
    :rtype: str
    """
    leading_text = elm.text and elm.text or ''
    result = [leading_text]

    for child in elm.getchildren():
        # Encoding is set to utf-8 because otherwise `ó` would
        # become `&#243;`
        child_value = etree.tostring(child, encoding='utf-8')
        # Decode to a string for later regexp and whitespace stripping
        child_value = child_value.decode('utf-8')
        result.append(child_value)

    if remove_namespaces:
        # Best way to remove the namespaces without having the parser complain
        # about producing invalid XML.
        result = [re.sub(' xmlns:?[^=]*="[^"]*"', '', v) for v in result]

    # Join the results and strip any surrounding whitespace
    result = u''.join(result).strip()
    return result


@timed
def parse_navigation_html_to_tree(html, id):
    """Parse the given ``html`` (an etree object) to a tree.
    The ``id`` is required in order to assign the top-level tree id value.
    """
    def xpath(x):
        return html.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    try:
        value = xpath('//*[@data-type="binding"]/@data-value')[0]
        is_translucent = value == 'translucent'
    except IndexError:
        is_translucent = False
    if is_translucent:
        id = TRANSLUCENT_BINDER_ID
    tree = {'id': id,
            'title': xpath('//*[@data-type="document-title"]/text()')[0],
            'contents': [x for x in _nav_to_tree(xpath('//xhtml:nav')[0])]
            }
    return tree


def _append_toc_type(li, tree):
    data_toc_type = li.get('data-toc-type')
    data_toc_target_type = li.get('data-toc-target-type')
    if data_toc_type is not None and len(data_toc_type) > 0:  # pragma: no cover
        tree['data-toc-type'] = data_toc_type
    if data_toc_target_type is not None and len(data_toc_target_type) > 0:  # pragma: no cover
        tree['data-toc-target-type'] = data_toc_target_type
    return tree


def _nav_to_tree(root):
    """Given an etree containing a navigation document structure
    rooted from the 'nav' element, parse to a tree:
    {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}
    """
    def expath(e, x):
        return e.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    for li in expath(root, 'xhtml:ol/xhtml:li'):
        is_subtree = bool([e for e in li.getchildren()
                           if e.tag[e.tag.find('}')+1:] == 'ol'])

        if is_subtree:
            # It's a sub-tree and have a 'span' and 'ol'.
            itemid = li.get('cnx-archive-uri', 'subcol')
            shortid = li.get('cnx-archive-shortid')
            yield _append_toc_type(li, {'id': itemid,
                                        # Title is wrapped in a span, div or some other element...
                                        'title': squash_xml_to_text(expath(li, '*')[0],
                                                                    remove_namespaces=True),
                                        'shortId': shortid,
                                        'contents': [x for x in _nav_to_tree(li)],
                                        })
        else:
            # It's a node and should only have an li.
            a = li.xpath('xhtml:a', namespaces=HTML_DOCUMENT_NAMESPACES)[0]
            yield _append_toc_type(li, {'id': a.get('href'),
                                        'shortid': li.get('cnx-archive-shortid'),
                                        'title': squash_xml_to_text(a, remove_namespaces=True)}
                                   )


@timed
def parse_metadata(html):
    """Parse metadata out of the given an etree object as ``html``."""
    parser = DocumentMetadataParser(html)
    return parser()


def parse_resources(html):
    """Return a list of resource names found in the html metadata section."""
    xpath = '//*[@data-type="resources"]//xhtml:li/xhtml:a'   # pragma: no cover
    for resource in html.xpath(xpath, namespaces=HTML_DOCUMENT_NAMESPACES):  # pragma: no cover
        yield {
            'id': resource.get('href'),
            'filename': resource.text.strip(),
        }


@timed
def reconstitute(html):
    """Given a file-like object as ``html``, reconstruct it into models."""
    html.seek(0)
    htree = etree.parse(html)
    xhtml = etree.tostring(htree, encoding='utf-8')
    return adapt_single_html(xhtml)


@timed
def adapt_single_html(html):
    """Adapts a single html document generated by
    ``.formatters.SingleHTMLFormatter`` to a ``models.Binder``
    """
    html_root = etree.fromstring(html)

    metadata = parse_metadata(html_root.xpath('//*[@data-type="metadata"]')[0])
    id_ = metadata['cnx-archive-uri'] or 'book'

    binder = Binder(id_, metadata=metadata)
    nav_tree = parse_navigation_html_to_tree(html_root, id_)

    body = html_root.xpath('//xhtml:body', namespaces=HTML_DOCUMENT_NAMESPACES)
    _adapt_single_html_tree(binder, body[0], nav_tree, top_metadata=metadata)

    return binder


@timed
def _adapt_single_html_tree(parent, elem, nav_tree, top_metadata,
                            id_map=None, depth=0):
    title_overrides = [i.get('title') for i in nav_tree['contents']]

    # A dictionary to allow look up of a document and new id using the old html
    # element id

    if id_map is None:
        id_map = {}

    def fix_generated_ids(page, id_map):
        """Fix element ids (remove auto marker) and populate id_map."""

        content = content_to_etree(page.content)

        new_ids = set()
        suffix = 0
        for element in content.xpath('.//*[@id]'):
            id_val = element.get('id')
            if id_val.startswith('auto_'):
                # It's possible that an auto_ prefix was injected using a page
                # ID that incorporated the page_ prefix. We'll remove that
                # first if it exists so the auto prefixing fix works whether
                # it is present or not.
                new_val = re.sub(r'^auto_page_', 'auto_', id_val)

                # We max split with two to avoid breaking up ID values that
                # may have originally included '_' and only undo the auto_{id}_
                # prefixing injected by a formatter
                new_val = new_val.split('_', 2)[-1]
                # Did content from different pages w/ same original id
                # get moved to the same page?
                if new_val in new_ids:   # pragma: no cover
                    while (new_val + str(suffix)) in new_ids:
                        suffix += 1
                    new_val = new_val + str(suffix)
            else:
                new_val = id_val
            new_ids.add(new_val)
            element.set('id', new_val)
            if id_val.startswith('page_'):
                # We want to map any references to the generated page ID
                # directly to the page
                id_map['#{}'.format(id_val)] = (page, '')  # pragma: no cover
            else:
                id_map['#{}'.format(id_val)] = (
                    page, new_val)   # pragma: no cover

        id_map['#{}'.format(page.id)] = (page, '')
        assert not (page.id and '@' in page.id)
        id_map['#{}'.format(page.id.split('@')[0])] = (page, '')

        page.content = etree_to_content(content)

    def fix_links(page, id_map):
        """Remap all intra-book links, replace with value from id_map."""

        content = content_to_etree(page.content)
        for i in content.xpath('.//*[starts-with(@href, "#")]',
                               namespaces=HTML_DOCUMENT_NAMESPACES):
            ref_val = i.attrib['href']
            if ref_val in id_map:
                target_page, target = id_map[ref_val]
                if page == target_page:  # pragma: no cover
                    i.attrib['href'] = f'#{target}'
                else:
                    target_id = target_page.id.split('@')[0]
                    if not target:  # link to page
                        i.attrib['href'] = f'/contents/{target_id}'  # pragma: no cover
                    else:
                        i.attrib['href'] = f'/contents/{target_id}#{target}'
            else:
                logging.error(f'Bad href: {ref_val}')  # pragma: no cover

        page.content = etree_to_content(content)

    def _compute_id(p, elem, key):
        """Compute id and shortid from parent uuid and child attr"""
        p_ids = [p.id.split('@')[0]]
        if 'cnx-archive-uri' in p.metadata and p.metadata['cnx-archive-uri']:
            p_ids.insert(0, p.metadata['cnx-archive-uri'].split('@')[0])

        p_uuid = None
        for p_id in p_ids:
            try:
                p_uuid = uuid.UUID(p_id)
                break
            except ValueError:  # pragma: no cover
                pass

        assert p_uuid is not None, 'Should always find a parent UUID'
        uuid_key = elem.get('data-uuid-key', elem.get('class', key))
        assert uuid_key is not None, (
            f'Could not compute id for {elem.get("data-type")} '
            f'on line {elem.sourceline}'
        )
        return str(uuid.uuid5(p_uuid, uuid_key))

    def _compute_shortid(ident_hash):
        """Compute shortId from uuid or ident_hash"""
        ver = None
        assert '@' in ident_hash
        (id_str, ver) = ident_hash.split('@')
        id_uuid = uuid.UUID(id_str)

        shortid = (base64.urlsafe_b64encode(id_uuid.bytes)[:8]).decode('utf-8')
        if ver:
            return '@'.join((shortid, ver))
        else:
            return shortid  # pragma: no cover

    # Adapt each <div data-type="unit|chapter|page|composite-page"> into
    # translucent binders, documents and composite documents
    for child in elem.getchildren():
        data_type = child.attrib.get('data-type')

        if data_type in ('unit', 'chapter', 'composite-chapter',
                         'page', 'composite-page'):
            # metadata munging for all node types, in one place
            metadata = parse_metadata(
                child.xpath('./*[@data-type="metadata"]')[0])

            # Handle version, id and uuid from metadata
            if not metadata.get('version'):
                if data_type.startswith('composite-'):  # pragma: no cover
                    if top_metadata.get('version') is not None:
                        metadata['version'] = top_metadata['version']
                elif parent.metadata.get('version') is not None:
                    metadata['version'] = parent.metadata['version']

            uuid_key = child.get('data-uuid-key')
            child_id = child.attrib.get('id')
            id_ = metadata.get('cnx-archive-uri') or (child_id
                                                      if not uuid_key
                                                      else None)
            if not id_:
                fallback_key = None
                if data_type in ('chapter', 'unit'):
                    fallback_key = metadata.get('title')
                id_ = _compute_id(parent, child, fallback_key)
                assert metadata.get('version')
                metadata['cnx-archive-uri'] = \
                    '@'.join((id_, metadata['version']))
                metadata['cnx-archive-shortid'] = None

            if (metadata.get('cnx-archive-uri') and
                    not metadata.get('cnx-archive-shortid')):
                metadata['cnx-archive-shortid'] = \
                    _compute_shortid(metadata['cnx-archive-uri'])

            shortid = metadata.get('cnx-archive-shortid')

            nav_tree_node = nav_tree['contents'].pop(0)
            if 'data-toc-type' in nav_tree_node:  # pragma: no cover
                metadata['data-toc-type'] = nav_tree_node['data-toc-type']
            if 'data-toc-target-type' in nav_tree_node:  # pragma: no cover
                metadata['data-toc-target-type'] = nav_tree_node['data-toc-target-type']

        if data_type in ['unit', 'chapter', 'composite-chapter']:
            # All the non-leaf node types
            title = html.HtmlElement(
                child.xpath('*[@data-type="document-title"]',
                            namespaces=HTML_DOCUMENT_NAMESPACES)[0]
            ).text_content().strip()
            metadata.update({'title': title,
                             'id': id_,
                             'shortId': shortid,
                             'type': data_type})
            binder = Binder(id_, metadata=metadata)
            # Recurse
            _adapt_single_html_tree(binder, child,
                                    nav_tree_node,
                                    top_metadata=top_metadata,
                                    id_map=id_map, depth=depth+1)
            parent.append(binder)
        elif data_type in ['page', 'composite-page']:
            # Leaf nodes
            metadata_nodes = child.xpath("*[@data-type='metadata']",
                                         namespaces=HTML_DOCUMENT_NAMESPACES)
            for node in metadata_nodes:
                child.remove(node)
            for key in child.keys():
                assert key not in ('itemtype', 'itemscope'), 'Seems true'

            document_body = content_to_etree('')
            document_body.append(child)
            contents = etree.tostring(document_body)
            model = {
                'page': Document,
                'composite-page': CompositeDocument,
            }[child.attrib['data-type']]

            document = model(id_, contents, metadata=metadata)
            parent.append(document)

            fix_generated_ids(document, id_map)  # also populates id_map
        else:
            assert data_type in ['metadata', None], \
                'Unknown data-type for child node'
            # Expected non-nodal child types
            pass  # pragma: no cover

    assert len(parent) == len(title_overrides), 'Nav TOC should HTML structure'

    for i, node in enumerate(parent):
        parent.set_title_for_node(node, title_overrides[i])

    # only fixup links after all pages
    # processed for whole book, to allow for foward links
    if depth == 0:
        for page in flatten_to_documents(parent):
            fix_links(page, id_map)


class DocumentMetadataParser:
    """Given a file-like object, parse out the metadata to a dictionary.
    This only parses the data. It does not validate it.
    """
    namespaces = HTML_DOCUMENT_NAMESPACES
    metadata_required_keys = (
        'title',
    )
    metadata_optional_keys = (
        'created', 'revised', 'language', 'subjects', 'keywords',
        'license_text', 'editors', 'illustrators', 'translators',
        'publishers', 'copyright_holders', 'authors', 'summary',
        'cnx-archive-uri', 'cnx-archive-shortid', 'derived_from_uri',
        'derived_from_title', 'version', 'canonical_book_uuid',
        'license_url', 'slug'
    )

    def __init__(self, elm_tree, raise_value_error=True):
        self._xml = elm_tree
        self.raise_value_error = raise_value_error

    def __call__(self):
        return self.metadata

    def parse(self, xpath, prefix=""):
        values = self._xml.xpath(prefix + xpath,
                                 namespaces=self.namespaces)
        return values

    @property
    def metadata(self):
        items = {}
        keyrings = (self.metadata_required_keys, self.metadata_optional_keys,)
        for keyring in keyrings:
            for key in keyring:
                # TODO On refactoring properties
                # raise an error on property access rather than outside of it
                # as is currently being done here.
                value = getattr(self, key.replace('-', '_'))
                if self.raise_value_error and \
                        key in self.metadata_required_keys and value is None:  # pragma: no cover
                    raise ValueError(
                        "A value for '{}' could not be found.".format(key))
                items[key] = value
        return items

    @property
    def title(self):
        items = self.parse('.//*[@data-type="document-title"]/text()')
        try:
            value = items[0]
        except IndexError:  # pragma: no cover
            value = None
        return value

    @property
    def summary(self):
        items = self.parse('.//*[@data-type="description"]')
        try:
            description = items[0]
            value = squash_xml_to_text(description).encode('utf-8')
        except IndexError:
            value = None
        return value

    @property
    def created(self):
        items = self.parse('.//xhtml:meta[@itemprop="dateCreated"]/@content')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def revised(self):
        # Grab revised from <meta> if available, otherwise check for a
        # corresponding data item
        md_items = self.parse(
            './/xhtml:meta[@itemprop="dateModified"]/@content'
        )
        data_items = self.parse('.//xhtml:*[@data-type="revised"]/@data-value')

        value = None
        for maybe_item in [md_items, data_items]:
            try:
                value = maybe_item[0]
                break
            except IndexError:
                continue

        return value

    @property
    def language(self):
        # look for lang attribute or schema.org meta tag
        items = self.parse('ancestor-or-self::*/@lang'
                           ' | ancestor-or-self::*/*'
                           '[@data-type="language"]/@content'
                           )
        try:
            value = items[-1]  # nodes returned in tree order, we want nearest
        except IndexError:  # pragma: no cover
            value = None
        return value

    @property
    def subjects(self):
        items = self.parse('.//xhtml:*[@data-type="subject"]/text()')
        return items

    @property
    def keywords(self):
        items = self.parse('.//xhtml:*[@data-type="keyword"]/text()')
        return items

    @property
    def license_url(self):
        # Three cases for location of metadata stanza:
        #  1. direct child of current node
        #  2. direct child of any ancestor
        #  3. Top of book (occurs when fetching from root)
        items = self.parse('ancestor-or-self::*/*[@data-type="metadata"]//*'
                           '[@data-type="license"]/@href'
                           ' | /xhtml:html/xhtml:body/*'
                           '[@data-type="metadata"]//*'
                           '[@data-type="license"]/@href'
                           )

        try:
            value = items[-1]  # doc order, want lowest (nearest)
        except IndexError:
            value = None
        return value

    @property
    def license_text(self):
        # Same as license_url
        items = self.parse('ancestor-or-self::*/*[@data-type="metadata"]//*'
                           '[@data-type="license"]/text()'
                           ' | /xhtml:html/xhtml:body/*'
                           '[@data-type="metadata"]//*'
                           '[@data-type="license"]/text()'
                           )
        try:
            value = items[-1]
        except IndexError:
            value = None
        return value

    def _parse_person_info(self, xpath):
        unordered = []
        for elm in self.parse(xpath):
            elm_id = elm.get('id', None)
            if len(elm) > 0:
                person_elm = elm[0]
                name = person_elm.text
                type_ = person_elm.get('data-type', None)
                id_ = person_elm.get('href', None)
            else:
                name = elm.text
                type_ = None
                id_ = None
            person = {'name': name, 'type': type_, 'id': id_}
            # Meta refinement allows these to be ordered.
            order = None
            refines_xpath_tmplt = """\
.//xhtml:meta[@refines="#{}" and @property="display-seq"]/@content"""
            if elm_id is not None:
                try:
                    order = self.parse(refines_xpath_tmplt.format(elm_id))[0]
                except IndexError:
                    order = 0  # Check for refinement failed, use constant
            unordered.append((order, person,))
        ordered = sorted(unordered, key=lambda x: x[0])
        values = [x[1] for x in ordered]
        return values

    @property
    def publishers(self):
        xpath = './/xhtml:*[@data-type="publisher"]'
        return self._parse_person_info(xpath)

    @property
    def editors(self):
        xpath = './/xhtml:*[@data-type="editor"]'
        return self._parse_person_info(xpath)

    @property
    def illustrators(self):
        xpath = './/xhtml:*[@data-type="illustrator"]'
        return self._parse_person_info(xpath)

    @property
    def translators(self):
        xpath = './/xhtml:*[@data-type="translator"]'
        return self._parse_person_info(xpath)

    @property
    def copyright_holders(self):
        xpath = './/xhtml:*[@data-type="copyright-holder"]'
        return self._parse_person_info(xpath)

    @property
    def authors(self):
        xpath = './/xhtml:*[@data-type="author"]'
        return self._parse_person_info(xpath)

    @property
    def cnx_archive_uri(self):
        items = self.parse(
            './/xhtml:*[@data-type="cnx-archive-uri"]/@data-value')
        if items:
            return items[0]

    @property
    def cnx_archive_shortid(self):
        items = self.parse(
            './/xhtml:*[@data-type="cnx-archive-shortid"]/@data-value')
        if items:
            return items[0]

    @property
    def version(self):
        items = self.parse(
            './/xhtml:*[@data-type="cnx-archive-uri"]/@data-value')
        if items:
            assert_msg = 'version should have an @ in it data-value="{}"'
            assert '@' in items[0], assert_msg.format(items[0])
            return items[0].split('@')[1]

    @property
    def derived_from_uri(self):
        items = self.parse('.//xhtml:*[@data-type="derived-from"]/@href')
        if items:
            return items[0]

    @property
    def derived_from_title(self):
        items = self.parse('.//xhtml:*[@data-type="derived-from"]/text()')
        if items:
            return items[0]

    @property
    def canonical_book_uuid(self):
        items = self.parse(
            './/xhtml:*[@data-type="canonical-book-uuid"]/@data-value')
        if items:
            return items[0]

    @property
    def slug(self):
        items = self.parse(
            './/xhtml:*[@data-type="slug"]/@data-value')
        if items:
            return items[0]


class DocumentPointerMetadataParser(DocumentMetadataParser):
    metadata_required_keys = (
        'title', 'cnx-archive-uri',
    )
    metadata_optional_keys = DocumentMetadataParser.metadata_optional_keys + (
        'license_url', 'summary', 'cnx-archive-shortid', 'data-toc-type', 'data-toc-target-type'
    )
