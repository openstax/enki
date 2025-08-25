import sys
from pathlib import Path

from lxml import etree
from lxml.html import XHTMLParser


NS_XHTML = "http://www.w3.org/1999/xhtml"
NS_MAP = {"h": NS_XHTML}


def say(msg):
    print(msg, file=sys.stderr)


def clean_toc(tree):
    toc = tree.xpath('//*[@id="toc"]')[0]
    print_exclude_class = "no-print"
    page_query = (
        '//*[@data-type="page"]['
        f'   contains(concat(" ", @class, " "), " {print_exclude_class} ")'
        ']'
    )
    chapter_query = (
        '//*[@data-type="chapter"]['
        '    not(.//*[@data-type="page" or @data-type="composite-page"])'
        ']'
    )
    unit_query = (
        '//*[@data-type="unit"]['
        '    not(.//*[@data-type="chapter" or @data-type="composite-chapter"])'
        ']'
    )
    did_match = False
    # order is important
    for query in (page_query, chapter_query, unit_query):
        elements = tree.xpath(query)
        for element in elements:
            el_id = ""
            data_type = element.attrib.get("data-type")
            assert data_type, "Element without data type"
            # units do not have ids
            if data_type in ("page", "chapter"):
                # pages have ids, chapters have a title with an id
                el_id = element.xpath('./@id | .//*[@id]/@id')[0]
                for tocItem in toc.xpath(
                    f'.//h:a[@href="#{el_id}"]/parent::h:li', namespaces=NS_MAP
                ):
                    container = tocItem.getparent()
                    container.remove(tocItem)
                    say(f'Removed link to: "{el_id}"')
                    if len(list(container.iterchildren())) == 0:
                        container.getparent().remove(container)
                        say("Removed container parent")
            element.getparent().remove(element)
            say(f'Removed element: "{el_id}"')
        did_match = did_match or (query == page_query and len(elements) > 0)
    if did_match:
        # trash empty units (but only if we made changes)
        empty_unit_query = (
            './/*[@data-toc-type="unit"][not(.//*[@data-toc-type])]'
        )
        for empty_unit in toc.xpath(empty_unit_query):
            empty_unit.getparent().remove(empty_unit)
            say("Removed unit ToC item")
    return did_match


def main():
    args = iter(sys.argv[1:])
    src = Path(next(args)).resolve(strict=True)
    dst = Path(next(args)).resolve()
    tree = etree.parse(src, XHTMLParser(recover=True))
    if clean_toc(tree):
        tree.write(str(dst), encoding="utf-8")


if __name__ == "__main__":
    main()  # pragma: no cover
