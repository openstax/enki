import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cnxepub.collation import reconstitute
from cnxepub.formatters import DocumentContentFormatter
from cnxepub.html_parsers import HTML_DOCUMENT_NAMESPACES
from cnxepub.models import flatten_to_documents, content_to_etree, etree_to_content
from lxml import etree
from lxml.builder import ElementMaker, E

from . import utils


def extract_slugs_from_tree(tree, data):
    """Given a tree with slugs create a flattened structure where slug data
    can be retrieved based upon id key
    """
    data.update({
        tree["id"].split('@')[0]: tree["slug"]
    })
    if "contents" in tree:
        for node in tree["contents"]:
            extract_slugs_from_tree(node, data)


def extract_slugs_from_binder(binder):
    """Given a binder return a dictionary that allows caller to retrieve
    computed slugs using ident_hash values"""

    # NOTE: The returned tree has 'id' values which are based upon ident_hash
    # fields in the provided model
    tree = utils.model_to_tree(binder)
    slugs = {}
    extract_slugs_from_tree(tree, slugs)
    return slugs


def main():
    """Main function"""
    xhtml_file = Path(sys.argv[1]).resolve(strict=True)
    metadata_file = Path(sys.argv[2]).resolve(strict=True)
    book_slug = sys.argv[3]
    out_dir = Path(sys.argv[4])

    with open(xhtml_file, "rb") as file:
        html_root = etree.parse(file)
        file.seek(0)
        binder = reconstitute(file)
        slugs = extract_slugs_from_binder(binder)

    with open(metadata_file, "r") as baked_json:
        baked_metadata = json.load(baked_json)
        book_toc_metadata = baked_metadata.get(binder.ident_hash)

    nav = html_root.xpath(
        "//xhtml:nav", namespaces=HTML_DOCUMENT_NAMESPACES)[0]

    toc_maker = ElementMaker(namespace=None,
                             nsmap={None: "http://www.w3.org/1999/xhtml"})
    toc = toc_maker.html(E.head(E.title("Table of Contents")),
                         E.body(nav))

    nav_links = toc.xpath("//xhtml:a", namespaces=HTML_DOCUMENT_NAMESPACES)

    for doc in flatten_to_documents(binder):
        id_with_context = f'{binder.ident_hash}:{doc.id}'

        module_etree = content_to_etree(doc.content)
        for link in nav_links:
            link_href = link.attrib['href']
            if not link_href.startswith('#'):
                continue
            if module_etree.xpath(
                    f"/xhtml:body/xhtml:div[@id='{link_href[1:]}']",
                    namespaces=HTML_DOCUMENT_NAMESPACES
            ):
                link.attrib['href'] = f'./{id_with_context}.xhtml'

        # Add metadata to same-book-different-module links.
        # The module in which same-book link targets reside is only fully known
        # at time of disassembly. Different pipelines can make use of this
        # metadata in different ways
        for node in module_etree.xpath(
                '//xhtml:a[@href and starts-with(@href, "/contents/")]',
                namespaces=HTML_DOCUMENT_NAMESPACES
        ):
            page_link = node.attrib["href"].split("/")[-1]
            # Link may have fragment
            if "#" in page_link:
                page_uuid, page_fragment = page_link.split("#")
            else:  # pragma: no cover
                page_uuid = page_link
                page_fragment = ''

            # This is either an intra-book link or inter-book link. We can
            # differentiate the latter by data-book-uuid attrib).
            if not node.attrib.get("data-book-uuid"):
                node.attrib["data-page-slug"] = slugs.get(page_uuid)
                node.attrib["data-page-uuid"] = page_uuid
                node.attrib["data-page-fragment"] = page_fragment

        doc.content = etree_to_content(module_etree)

        # Inject some styling and JS for QA
        xml_parser = etree.XMLParser(ns_clean=True)
        root = etree.XML(bytes(DocumentContentFormatter(doc)), xml_parser)
        head = root.xpath("//xhtml:head", namespaces=HTML_DOCUMENT_NAMESPACES)

        if not head:
            head = etree.Element("head")
            root.insert(0, head)

        style = etree.Element("style")
        script = etree.Element("script")

        style.text = u'''
            /* STYLING_FOR_DEVS */
            /* Linking to a specific element should highlight the element */
            :target {
                background-color: #ffffcc;
                border: 1px dotted #000000;

                animation-name: cssAnimation;
                animation-duration: 10s;
                animation-timing-function: ease-out;
                animation-delay: 0s;
                animation-fill-mode: forwards;
            }
            @keyframes cssAnimation {
                to {
                    background-color: initial;
                    border: initial;
                }
            }

            /* Style footnotes so that they stand out */
            [role="doc-footnote"] {
                background-color: #ffcccc;
                border: 1px dashed #ff0000;
            }
            [role="doc-footnote"]:before { content: "FOOTNOTE " ; }

            /* Show a permalink when hovering over a heading or paragraph */
            *:not(:hover) > a.-dev-permalinker { display: none; }
            * > a.-dev-permalinker {
                margin-left: .1rem;
                text-decoration: none;
            }
        '''

        script.text = u'''//<![CDATA[
            // SCRIPTS_FOR_DEVS
            window.addEventListener('load', () => {
                const pilcrow = '¶'

                function addPermalink(parent, id) {
                    const link = window.document.createElement('a')
                    link.classList.add('-dev-permalinker')
                    link.setAttribute('href', '#' + id)
                    link.textContent = pilcrow
                    parent.appendChild(link)
                }

                const paragraphs = Array.from(
                    document.querySelectorAll('p[id]')
                )
                paragraphs.forEach(p => addPermalink(p, p.getAttribute('id')) )

                const headings = Array.from(
                    document.querySelectorAll(
                        '*[id] > h1, *[id] > h2, *[id] > h3, ' +
                        '*[id] > h4, *[id] > h5, *[id] > h6'
                    )
                )
                headings.forEach(h => addPermalink(
                    h, h.parentElement.getAttribute('id'))
                )
            })
        // ]]>'''

        head.append(style)
        head.append(script)

        with open(f"{out_dir / id_with_context}.xhtml", "wb") as out:
            out.write(etree.tostring(root))

        with open(
                f"{out_dir / id_with_context}-metadata.json", "w"
        ) as json_out:
            # Incorporate metadata from disassemble step while setting defaults
            # for cases like composite pages which may not have metadata from
            # previous stages
            json_metadata = {
                "slug": slugs.get(doc.id),
                "title": doc.metadata.get("title"),
                "abstract": None,
                "id": doc.id,
                "revised": datetime.now(timezone.utc).isoformat()
            }

            # Add / override metadata from baking if available
            json_metadata.update(baked_metadata.get(doc.ident_hash, {}))

            json.dump(
                json_metadata,
                json_out
            )

    with open(f"{out_dir}/{book_slug}.toc.xhtml", "wb") as out:
        out.write(etree.tostring(toc, encoding="utf8", pretty_print=True))

    with open(f"{out_dir}/{book_slug}.toc-metadata.json", "w") as toc_json:
        json.dump(book_toc_metadata, toc_json)


if __name__ == "__main__":  # pragma: no cover
    main()
