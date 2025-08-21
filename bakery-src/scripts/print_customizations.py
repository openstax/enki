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
    pageQuery = f'//*[@data-type="page"][contains(@class, "{print_exclude_class}")]'
    # Chapters that contain only print-excluded pages
    chapterQuery = (
        '//*[@data-type="chapter"]['
        '    not(.//*['
        '        @data-type="page" and '
        f'       not(contains(@class, "{print_exclude_class}"))'
        '    ])'
        ']'
    )
    for query in [pageQuery, chapterQuery]:
        for element in tree.xpath(query):
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
    # trash empty units
    empty_unit_query = (
        './/*[@data-toc-type="unit"]['
        '   count(.//*[@data-toc-type="chapter"])=0'
        ']'
    )
    for empty_unit in toc.xpath(empty_unit_query):
        empty_unit.getparent().remove(empty_unit)
        say("Removed unit ToC item")


def main():
    args = iter(sys.argv[1:])
    src = Path(next(args)).resolve(strict=True)
    dst = Path(next(args)).resolve()
    tree = etree.parse(src, XHTMLParser(recover=True))
    clean_toc(tree)
    tree.write(str(dst), encoding="utf-8")


if __name__ == "__main__":
    main()
