# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import asyncio
import os
import logging
from copy import copy
from functools import lru_cache

import jinja2
import lxml.html
from lxml import etree

import requests
from requests.exceptions import RequestException
import backoff

from .converters import cnxml_abstract_to_html
from .templates.exercise_template import EXERCISE_TEMPLATE
from .xml_utils import (
    HTML_DOCUMENT_NAMESPACES,
    etree_from_str,
    etree_to_content,
    squash_xml_to_text,
    xpath_html,
)
from .async_job_queue import AsyncJobQueue
from . import h5p_injection

logger = logging.getLogger("nebuchadnezzar")


def insert_includes(root_elem, page_uuids, includes, threads=20):
    async def async_exercise_fetching():
        loop = asyncio.get_running_loop()
        for match, proc, concurrent in includes:
            if concurrent:
                job_queue = AsyncJobQueue(threads)
                async with job_queue as q:
                    for elem in xpath_html(root_elem, match):
                        q.put_nowait(
                            loop.run_in_executor(None, proc, elem, page_uuids)
                        )
                if len(job_queue.errors) != 0:
                    raise Exception(
                        "The following errors occurred: \n" +
                        "\n###### NEXT ERROR ######\n".join(job_queue.errors)
                    )
            else:
                for elem in xpath_html(root_elem, match):
                    proc(elem, page_uuids)

    asyncio.run(async_exercise_fetching())


def update_ids(document):
    """Generate unique ids for html elements in page content so that it's
    possible to link to them.
    """
    content = document.content
    document_id = document.metadata["uuid"]
    xpath = ".//*[@id]"

    old_id_to_new_id = {}
    # Step 1: prefix all ids with the document so they are unique when all
    # the documents are combined
    for elem in xpath_html(content, xpath):
        old_id = elem.attrib.get("id")
        new_id = "auto_{}_{}".format(document_id, old_id)
        elem.attrib["id"] = new_id
        old_id_to_new_id[old_id] = new_id

    # Step 2: redirect links to elements with now prefixed ids
    for a in xpath_html(content, "//a[@href]|//xhtml:a[@href]"):
        href = a.attrib["href"]
        if href.startswith("#") and href[1:] in old_id_to_new_id:
            a.attrib["href"] = "#{}".format(old_id_to_new_id[href[1:]])


@lru_cache(maxsize=None)
def _get_external_document(p):
    from .models.book_part import BookPart

    return BookPart.doc_from_file(p)


def resolve_module_links(document, docs_by_id, path_resolver):
    """Resolve module links
    <a href="/contents/{PAGE_ID} (and maybe fragment?)"> (other-book link)
    <a href="#page_{PAGE_ID}"> (same-book link)
    <a href="#auto_{PAGE_ID}_{TARGET_ID}"> (element on a page)
    """
    for link in document.content.xpath("//*[@href]"):
        href = link.get("href", "").strip()
        if len(href) == 0:  # pragma: no cover
            logger.warning(f"Empty link in \"{document.metadata['id']}\"")
            continue
        if not href.startswith("/m"):  # pragma: no cover
            continue
        fragment_idx = href.find("#")
        if fragment_idx != -1:
            module_id = href[1:fragment_idx]
            fragment = href[fragment_idx:].replace("#", "_")
            fmt_str = f"#auto_{{}}{fragment}"
        else:
            module_id = href[1:]
            fmt_str = "#page_{}"
        target_document = docs_by_id.get(module_id, None)
        if target_document is not None:
            new_href = fmt_str.format(target_document.metadata["uuid"])
        else:
            target_document = _get_external_document(
                path_resolver.get_module_path(module_id)
            )
            uuid = target_document.metadata["uuid"]
            new_href = f"/contents{href.replace(module_id, uuid)}"
        link.set("href", new_href)


def _create_html_template():
    def isdict(v):  # pragma: no cover
        return isinstance(v, dict)

    template_env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    return template_env.from_string(HTML_DOCUMENT, globals={"isdict": isdict})


def _create_html_doc(metadata, content, is_translucent=False, root_attrs={}):
    template = _create_html_template()
    return template.render(
        metadata=metadata,
        content=content,
        # Note: not used, probably safe to remove
        is_translucent=is_translucent,
        root_attrs=root_attrs,
    ).encode("utf-8")


def _col_to_html(book_part):
    return _create_html_doc(
        metadata=book_part.metadata,
        content=tree_to_html(book_part).decode("utf-8"),
        is_translucent=book_part.is_subcol,
    )


def _doc_to_html(document):
    # Determine if we've been fed a full XHTML page, with a <body> tag:
    bods = xpath_html(
        document.content,
        "//*[self::body|self::xhtml:body]",
    )
    assert bods, "Content must have <body>"
    root = bods[0]
    # TODO: maybe include this summary in parse_metadata instead. Granted, it
    #       seems most relevant here
    metadata = copy(document.metadata)
    metadata["summary"] = metadata.pop("abstract")
    metadata["summary"] = metadata["summary"] and metadata["summary"] or None
    if metadata["summary"] is not None:
        s = cnxml_abstract_to_html(metadata["summary"])
        s = etree_from_str(s)
        metadata["summary"] = squash_xml_to_text(s, remove_namespaces=True)
    return _create_html_doc(
        metadata=metadata,
        content=etree_to_content(root, strip_root_node=True),
        root_attrs={k: root.get(k) for k in root.keys()},
    )


def _get_node_type(book_part, parent=None):
    """If node is a document, the type is page.
    If node is a binder with no parent, the type is book.
    If node is a subcol, the type is either chapters (only
    contain pages) or unit (contains at least one subcol).
    """

    if book_part.is_doc:
        return "page"
    elif book_part.is_col and parent is None:
        return "book"
    elif any(child.is_subcol for child in book_part.children):
        return "unit"
    else:
        return "chapter"


def assemble_collection(collection):
    def recursive_build(subcol, elem):
        canonical_parent_type = _get_node_type(subcol)
        for book_part in subcol.children:
            canonical_node_type = _get_node_type(
                book_part, canonical_parent_type
            )
            attrs = {"data-type": canonical_node_type}
            # This could probably be: if not book_part.is_subcol
            node_id = book_part.metadata.get("uuid")
            if node_id:
                # Page IDs may start with a number when they're UUIDs, so we
                # prefix the value if it's not already there
                # (https://github.com/openstax/cnx/issues/1514)
                attrs["id"] = (
                    f"page_{node_id}"
                    if book_part.is_doc and not node_id.startswith("page_")
                    else node_id
                )

            child_elem = etree.SubElement(elem, "div", **attrs)
            if book_part.is_subcol or book_part.is_col:
                # Build the subcol to html (making a nav element, etc.)
                html = _col_to_html(book_part)
                doc_root = etree_from_str(html)
                # Extract the metadata
                metadata = xpath_html(
                    doc_root,
                    '//xhtml:body/xhtml:div[@data-type="metadata"]',
                )
                if metadata:
                    child_elem.append(metadata[0])

                # And now the top-level title, too
                etree.SubElement(
                    child_elem, "h1", **{"data-type": "document-title"}
                ).text = book_part.metadata["title"]
                recursive_build(book_part, child_elem)
            elif book_part.is_doc:
                html = _doc_to_html(book_part)
                doc_root = etree_from_str(html)
                body = xpath_html(doc_root, "//xhtml:body")[0]
                for c in body.iterchildren():
                    child_elem.append(c)
                for a in body.attrib:
                    if not (a.startswith("item")):
                        child_elem.set(a, body.get(a))

    root = etree_from_str(_col_to_html(collection))
    body = xpath_html(root, "//xhtml:body")[0]
    recursive_build(collection, body)
    return root


def parse_context_tags(tags, elem, page_uuids):
    if not tags:
        return

    # Annotate exercise with required context, if it exists
    modules, feature = [], ""
    for tag in tags:
        if "context-cnxmod:" in tag:
            modules.append(tag.split(":")[1])
        if "context-cnxfeature:" in tag:
            # Note: Assuming this tag will never be duplicated with
            # multiple values in the exercise data
            feature = tag.split(":")[1]

    # It's possible that the feature tag is not present, or present but
    # not valid (e.g. value of "context-cnxfeature:").
    if not feature:
        return

    # There may be multiple `context-cnxmod:{uuid}` tags, each of which
    # could be the parent page for this exercise, a different page in
    # this book, or even invalid altogether. We'll prefer the first,
    # fallback # to the second, and error in the last case.

    parent_page_elem = elem.xpath('ancestor::*[@data-type="page"]')[0]
    parent_page_uuid = parent_page_elem.get("id")
    if parent_page_uuid.startswith("page_"):
        # Strip `page_` prefix from ID to get UUID
        parent_page_uuid = parent_page_uuid.split("page_")[1]

    candidate_uuids = set(modules) & set(page_uuids)

    # Check if the target feature ID is on the parent page for this
    # exercise. If so, that takes priority over any context-cnxmod tag
    # values, and should be picked even in cases where the parent page
    # doesn't match one of the exercise tags. If the feature exists,
    # we make sure the parent page UUID is included in candidate_uuids.
    # Otherwise, remove parent page from candidate UUIDs.
    maybe_feature = parent_page_elem.find(
        './/*[@id="auto_{}_{}"]'.format(parent_page_uuid, feature)
    )
    if maybe_feature is None:
        candidate_uuids.discard(parent_page_uuid)
    else:
        candidate_uuids.add(parent_page_uuid)

    # No valid page UUIDs in exercise data
    assert_msg = "No candidate uuid for exercise feature {} href={}"
    assert len(candidate_uuids) > 0, assert_msg.format(
        feature, elem.get("href")
    )

    if parent_page_uuid in candidate_uuids:
        target_module = parent_page_uuid
    else:
        # Use an UUID in the intersection of page UUIDs and tag UUIDs
        # This is somewhat arbritrary, but if we hit this scenario with
        # more than one UUID in the set things have gone pretty
        # unexpectedly
        target_module = candidate_uuids.pop()
    return target_module, feature


def annotate_exercise(exercise, elem, target_module, feature):
    # As a final validation check, confirm the feature is on the target
    # module and otherwise raise
    #
    # NOTE: The following uses xpath() and find() together which may seem
    # bizarre, but it's a work around for the fact that using just an
    # xpath of '//*[@id="auto_{}_{}"]' results in seg faults when there
    # are multiple threads due to the tree editing that occurs in
    # _replace_exercises.
    target_ref = "auto_{}_{}".format(target_module, feature)
    feature_element = elem.xpath("/*")[0].find(
        './/*[@id="{}"]'.format(target_ref)
    )

    assert_msg = "Feature {} not in {} href={}".format(
        feature, target_module, elem.get("href")
    )
    assert feature_element is not None, assert_msg

    exercise["required_context"] = {}
    exercise["required_context"]["module"] = target_module
    exercise["required_context"]["feature"] = feature
    exercise["required_context"]["ref"] = target_ref


def get_exercise_placeholder(message, data_type):
    XHTML = HTML_DOCUMENT_NAMESPACES["xhtml"]
    div = etree.Element(
        f"{{{XHTML}}}div",
        {},
        nsmap=HTML_DOCUMENT_NAMESPACES,
        xmlns=XHTML
    )
    etree.SubElement(
        div,
        f"{{{XHTML}}}span",
        {"data-type": data_type},
        nsmap=HTML_DOCUMENT_NAMESPACES,
    ).text = message
    return div


def get_missing_exercise_placeholder(uri, exercise_id):
    logger.warning("MISSING EXERCISE: {}".format(uri))
    return get_exercise_placeholder(
        f"MISSING EXERCISE: tag:{exercise_id}", "missing-exercise"
    )


def parse_exercise_html_to_etree(s: str, content_id: str):
    try:
        return etree_from_str(f"<div>{s}</div>")
    except etree.XMLSyntaxError as xse:
        logger.warning(
            f"WARNING: Falling back to HTML parsing for: {content_id}\n"
            f"\tUnderlying XML error: {xse}"
        )

        padding = "#" * 35
        comment = etree.Comment(
            "\n"
            f"{padding}WARNING{padding}\n"
            "Fell back to HTML parsing for the following content\n"
            f"{padding}WARNING{padding}\n"
        )
        body = etree.HTML(s, None)[0]
        body.insert(0, comment)
        return body


def get_parent_page_uuid(elem):
    parent_page_elem = elem.xpath('ancestor::*[@data-type="page"]')[0]
    return parent_page_elem.get("id").lstrip("page_")


def exercise_callback_factory(match, url_template, token=None):
    """Create a callback function to replace an exercise by fetching from
    a server."""

    def _annotate_exercise(elem, data, page_uuids):
        """Annotate exercise based upon tag data"""
        exercise = data["items"][0]
        tags = exercise.get("tags", [])
        context = parse_context_tags(tags, elem, page_uuids)
        if context is not None:
            target_module, feature = context
            annotate_exercise(exercise, elem, target_module, feature)

    @backoff.on_exception(
        backoff.expo,
        RequestException,
        max_time=60 * 15,
        giveup=lambda e: (
            # Give up on non-request error
            not isinstance(e, RequestException) or (
                # Give up if the status code is something like 404, 403, etc.
                e.response is not None and
                e.response.status_code in range(400, 500)
            )
        ),
        jitter=backoff.full_jitter,
        raise_on_giveup=True
    )
    def _replace_exercises(elem, page_uuids):
        item_code = elem.get("href")[len(match):]
        url = url_template.format(itemCode=item_code)
        exercise_class = elem.get("class")
        if token:
            headers = {"Authorization": "Bearer {}".format(token)}
            res = requests.get(url, headers=headers)
        else:
            res = requests.get(url)

        assert res
        # grab the json exercise, run it through Jinja2 template,
        # replace element w/ it
        exercise = res.json()

        if exercise["total_count"] == 0:
            root_elem = get_missing_exercise_placeholder(url, item_code)
        else:
            parent_page_uuid = get_parent_page_uuid(elem)
            exercise["items"][0]["url"] = url
            exercise["items"][0]["class"] = exercise_class
            _annotate_exercise(elem, exercise, page_uuids)
            assert len(exercise["items"]) == 1, \
                'Exercise "items" array is nonsingular'
            exercise_content = exercise["items"][0]
            html = render_exercise(exercise_content, parent_page_uuid)
            root_elem = parse_exercise_html_to_etree(html, item_code)

        parent = elem.getparent()
        for child in root_elem:
            parent.insert(parent.index(elem), child)
        parent.remove(elem)  # Special case - assumes single wrapper elem

    xpath = '//xhtml:a[contains(@href, "{}")]'.format(match)
    return (xpath, _replace_exercises, True)


def interactive_callback_factory(
    match,
    path_resolver,
    docs_by_id,
    media_handler,
):
    """Create a callback function to replace an exercise by fetching from
    the repository."""

    def _annotate_exercise(elem, exercise, metadata, page_uuids):
        """Annotate exercise based upon tag data"""
        split_contexts = [
            ctx.split("#", 1)
            for ctx in metadata.get("context", [])
            if "#" in ctx
        ]
        if len(split_contexts) > 0:
            # Get the uuid of the page the content is being injected into
            parent_page_uuid = get_parent_page_uuid(elem)
            context_uuid, context_elem_id = None, None
            specificity_by_name = {
                "default": -1,
                "diff_book": 0,
                "same_book": 1,
                "same_page": 2,
            }
            last_specificity = specificity_by_name["default"]
            # If multiple contexts are valid, we use the most specific one
            for module_id, elem_id in split_contexts:
                if module_id in docs_by_id:
                    document = docs_by_id[module_id]
                    specificity = specificity_by_name["same_book"]
                else:  # pragma: no cover
                    # Ignore context linking to different book for now
                    # until a more formal decision is made
                    # # If we already found one more specific, we can skip and
                    # # avoid loading additional documents
                    # if last_specificity > specificity_by_name["diff_book"]:
                    #     continue
                    # module_path = path_resolver.get_module_path(module_id)
                    # document = _get_external_document(module_path)
                    # specificity = specificity_by_name["diff_book"]
                    continue

                target_module = document.metadata["uuid"]

                if target_module == parent_page_uuid:
                    specificity = specificity_by_name["same_page"]

                if specificity < last_specificity:
                    continue

                # Search assembled document for the referenced element
                maybe_feature = elem.xpath(
                    f'//*[@id = "auto_{target_module}_{elem_id}"]'
                )
                if len(maybe_feature) > 0:
                    context_uuid, context_elem_id = target_module, elem_id
                    last_specificity = specificity
            assert context_uuid is not None and context_elem_id is not None, \
                f'Invalid context: {exercise["nickname"]}'
            annotate_exercise(exercise, elem, context_uuid, context_elem_id)
        else:
            tags = metadata.get("tags", [])
            context = parse_context_tags(tags, elem, page_uuids)
            if context is None:
                return
            target_module, feature = context
            annotate_exercise(exercise, elem, target_module, feature)

    def _replace_exercises(elem, page_uuids):
        nickname = elem.get("href")[len(match) + 1:]
        interactive_path = path_resolver.get_public_interactives_path(
            nickname
        )
        relpath = os.path.relpath(
            interactive_path,
            os.path.join(path_resolver.book_container.root_dir, "..")
        )
        css_class = elem.get("class")
        h5p_in = h5p_injection.load_h5p_interactive(interactive_path)

        if not h5p_in:
            root_elem = get_missing_exercise_placeholder(relpath, nickname)
        else:
            parent_page_uuid = get_parent_page_uuid(elem)
            attachments = h5p_in["metadata"]["attachments"]
            exercise = {}
            exercise["nickname"] = nickname
            exercise["tags"] = h5p_injection.tags_from_metadata(
                h5p_in["metadata"]
            )
            exercise["url"] = relpath
            exercise["class"] = css_class
            exercise["is_vocab"] = False
            exercise["stimulus_html"] = h5p_in["content"].get(
                "questionSetStimulus", ""
            )

            try:
                exercise["questions"] = h5p_injection.questions_from_h5p(
                    nickname, h5p_in
                )
                _annotate_exercise(
                    elem, exercise, h5p_in["metadata"], page_uuids
                )

                html = render_exercise(exercise, parent_page_uuid)
                root_elem = parse_exercise_html_to_etree(html, nickname)

                h5p_injection.handle_attachments(
                    attachments,
                    nickname,
                    root_elem,
                    media_handler,
                )
                for attachment in attachments:
                    resource_abs_path = path_resolver.find_interactives_path(
                        nickname, attachment
                    )
                    if resource_abs_path is not None:  # pragma: no cover
                        logger.warning(
                            "WARNING: Possible unused resource: "
                            f"{nickname}:{resource_abs_path}"
                        )
            except h5p_injection.UnsupportedLibraryError as ule:
                library = ule.args[0]
                root_elem = get_exercise_placeholder(
                    f"UNSUPPORTED LIBRARY: {library}", "unsupported-library"
                )

        parent = elem.getparent()
        for child in root_elem:
            parent.insert(parent.index(elem), child)
        parent.remove(elem)  # Special case - assumes single wrapper elem

    xpath = '//xhtml:a[contains(@href, "{}")]'.format(match)
    return (xpath, _replace_exercises, False)


def render_exercise(exercise, parent_page_uuid):
    return EXERCISE_TEMPLATE.render(
        data=exercise, parent_page_uuid=parent_page_uuid
    )


HTML_DOCUMENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:lrmi="http://lrmi.net/the-specification"
      xmlns:bib="http://bibtexml.sf.net/"
      xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute"
      xmlns:qml="http://cnx.rice.edu/qml/1.0"
      xmlns:datadev="http://dev.w3.org/html5/spec/#custom"
      xmlns:mod="http://cnx.rice.edu/#moduleIds"
      xmlns:md="http://cnx.rice.edu/mdml"
      xmlns:c="http://cnx.rice.edu/cnxml"
      {% if metadata.get('language') %}
      lang="{{ metadata['language'] }}"
      {% endif %}
      >
  <head itemscope="itemscope"
        itemtype="http://schema.org/Book"
        >

    <title>{{ metadata['title']|e }}</title>
    {% if metadata.get('language') %}
    <meta itemprop="inLanguage"
          data-type="language"
          content="{{ metadata['language'] }}"
          />
    {% endif %}

    {# TODO Include this based on the feature being present #}
    <!-- These are for discoverability of accessible content. -->
    <meta itemprop="accessibilityFeature" content="MathML" />
    <meta itemprop="accessibilityFeature" content="LaTeX" />
    <meta itemprop="accessibilityFeature" content="alternativeText" />
    <meta itemprop="accessibilityFeature" content="captions" />
    <meta itemprop="accessibilityFeature" content="structuredNavigation" />

    {# TODO
       <meta refines="#<html-id>" property="display-seq" content="<ord>" />
     #}

    {% if metadata.get('created') %}
    <meta itemprop="dateCreated"
          content="{{ metadata['created'] }}"
          />
    {% endif %}
    <meta itemprop="dateModified"
          content="{{ metadata['revised'] }}"
          />
  </head>
  <body itemscope="itemscope"
        itemtype="http://schema.org/Book"
      {% for attr,value in root_attrs.items() %}
        {{ attr }}="{{ value }}"
      {%- endfor %}
        >
    <div data-type="metadata" style="display: none;">
      <h1 data-type="document-title" itemprop="name">{{ \
              metadata['title']|e }}</h1>
      {% if metadata.get('revised') %}
      <span data-type="revised" data-value="{{ \
          metadata['revised'] }}" />
      {% endif %}
      {% if metadata.get('canonical_book_uuid') %}
      <span data-type="canonical-book-uuid" data-value="{{ \
          metadata['canonical_book_uuid'] }}" />
      {% endif %}
      {% if metadata.get('slug') %}
      <span data-type="slug" data-value="{{ \
          metadata['slug'] }}" />
      {% endif %}
      {% if is_translucent %}
      <span data-type="binding" data-value="translucent" />
      {%- endif %}
      {% if metadata.get('cnx-archive-uri') %}
      <span data-type="cnx-archive-uri" data-value="{{ \
          metadata['cnx-archive-uri'] }}" />
      {% if metadata.get('cnx-archive-shortid') %}
      <span data-type="cnx-archive-shortid" data-value="{{ \
          metadata['cnx-archive-shortid'] }}" />
      {%- endif %}
      {%- endif %}
      {% if metadata.get('authors') %}

      <div class="authors">
        By:
        {% for author in metadata['authors'] -%}
          <span id="{{ '{}-{}'.format('author', loop.index) }}"
                itemscope="itemscope"
                itemtype="http://schema.org/Person"
                itemprop="author"
                data-type="author"
                >
            <a href="{{ author['id'] }}"
               itemprop="url"
               data-type="{{ author['type'] }}"
               >{{ author['name']|e }}</a>
          </span>{% if not loop.last %}, {% endif %}
        {%- endfor %}

        Edited by:
        {% set person_type = 'editor' %}
        {% set person_itemprop_name = 'editor' %}
        {% set person_key = 'editors' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name']|e }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}

        Illustrated by:
        {% set person_type = 'illustrator' %}
        {% set person_itemprop_name = 'illustrator' %}
        {% set person_key = 'illustrators' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name']|e }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}

        Translated by:
        {% set person_type = 'translator' %}
        {% set person_itemprop_name = 'contributor' %}
        {% set person_key = 'translators' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name']|e }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}

      </div>
      {%- endif %}
      {% if metadata.get('publishers') %}

      <div class="publishers">
        Published By:
        {% set person_type = 'publisher' %}
        {% set person_itemprop_name = 'publisher' %}
        {% set person_key = 'publishers' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name']|e }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}
      </div>
      {%- endif %}
      {% if metadata.get('derived_from_uri') %}

      <div class="derived-from">
        Derived from:
        <a href="{{ metadata['derived_from_uri'] }}"
           itemprop="isDerivedFromURL"
           data-type="derived-from"
           >{{ metadata['derived_from_title']|escape }}</a>
      </div>
      {%- endif %}
      {% if metadata.get('copyright-holder') or metadata.get('license_url') %}

      <div class="permissions">
        {% if metadata['copyright_holders'] %}
        <p class="copyright">
          Copyright:
          {% set person_type = 'copyright-holder' %}
          {% set person_itemprop_name = 'copyrightHolder' %}
          {% set person_key = 'copyright_holders' %}
          {% for person in metadata[person_key] -%}
            {% if isdict(person) %}
              <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                    itemscope="itemscope"
                    itemtype="http://schema.org/Person"
                    itemprop="{{ person_type }}"
                    data-type="{{ person_type }}"
                    >
                <a href="{{ person['id'] }}"
                   itemprop="url"
                   data-type="{{ person['type'] }}"
                   >{{ person['name']|e }}</a>
              </span>{% if not loop.last %}, {% endif %}
            {% else %}
              <span itemprop="{{ person_type }}"
                    data-type="{{ person_type }}"
                >person</span>{% if not loop.last %}, {% endif %}
            {% endif %}
          {%- endfor %}
        </p>
        {% endif %}
        <p class="license">
          Licensed:
          <a href="{{ metadata['license_url'] }}"
             itemprop="dc:license,lrmi:useRightsURL"
             data-type="license"
             >{{ metadata['license_text']|e }}</a>
        </p>
      </div>
      {%- endif %}
      {% if metadata['summary'] %}

      <div class="description"
           itemprop="description"
           data-type="description"
           >
        {{ metadata['summary'] }}
      </div>
      {%- endif %}
      {% for keyword in metadata['keywords'] -%}
      <div itemprop="keywords" data-type="keyword">{{ keyword|escape }}</div>
      {%- endfor %}
      {% for subject in metadata['subjects'] -%}
      <div itemprop="about" data-type="subject">{{ subject|escape }}</div>
      {%- endfor %}
    </div>

   {{ content }}
  </body>
</html>
"""


def html_listify(tree, root_xl_element):
    for book_part in tree.children:
        li_elm = etree.SubElement(root_xl_element, "li")
        if book_part.is_subcol or book_part.is_col:
            span_elm = lxml.html.fragment_fromstring(
                book_part.metadata["title"], create_parent="span"
            )
            li_elm.append(span_elm)
            elm = etree.SubElement(li_elm, "ol")
            html_listify(book_part, elm)
        else:
            page_uuid = book_part.metadata["uuid"]
            a_elm = lxml.html.fragment_fromstring(
                book_part.metadata["title"], create_parent="a"
            )
            a_elm.set("href", "".join(["#page_", page_uuid]))
            li_elm.append(a_elm)
            li_elm.set(
                "cnx-archive-uri", book_part.metadata["cnx-archive-uri"]
            )


def tree_to_html(tree):
    nav = etree.Element("nav")
    nav.set("id", "toc")
    ol = etree.SubElement(nav, "ol")
    html_listify(tree, ol)
    return etree.tostring(nav)
