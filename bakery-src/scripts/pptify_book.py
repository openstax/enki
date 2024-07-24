from dataclasses import dataclass
import sys
import subprocess
import shlex
from pathlib import Path
from typing import Iterable, ParamSpec, TypeVar
from collections.abc import Callable
import re
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree
from lxml.builder import ElementMaker
import pptx  # python-pptx
import pptx.util
import pptx.shapes
from pptx.shapes.picture import Picture
from pptx.shapes.base import BaseShape
from pptx.slide import Slide
from slugify import slugify


Param = ParamSpec("Param")
RetType = TypeVar("RetType")


def class_xpath(class_name: str):
    return f'contains(concat(" ", @class, " "), " {class_name} ")'


def memoize(func: Callable[Param, RetType]):
    last_value = -1
    instance = None

    def wrapper(*args: Param.args, **kwargs: Param.kwargs):
        nonlocal instance, last_value
        should_run = False
        new_value = hash(tuple(map(hash, (*args, *kwargs.items()))))
        if new_value != last_value:
            last_value = new_value
            should_run = True
        if instance is None or should_run:
            instance = func(*args, **kwargs)
        return instance

    return wrapper


class Element:
    def __init__(self, element):
        self._element = element

    @property
    def element(self):
        return self._element

    def get(self, name: str):  # pragma: no cover
        return self._element.get(name)

    def xpath(self, p: str, *, namespaces=None):
        _namespaces = {"h": "http://www.w3.org/1999/xhtml"}
        if namespaces is not None:  # pragma: no cover
            _namespaces.update(namespaces)
        return self._element.xpath(p, namespaces=_namespaces)

    def xpath1(self, p: str):
        return self.xpath(p)[0]

    def xpath1_or_none(self, p: str):
        try:
            return self.xpath1(p)
        except IndexError:
            return None


class BookElement(Element):
    @memoize
    def get_title(self):
        return self.xpath1(
            './/*[@data-type="metadata"]/*[@data-type="document-title"]/text()'
        ).strip()

    def get_number(self):  # pragma: no cover
        raise NotImplementedError()


class Captioned(Element):
    @memoize
    def get_caption_elem(self):
        return self.xpath1(f'./*[{class_xpath("os-caption-container")}]')

    def has_caption(self):
        return (
            self.xpath1_or_none(f'.//*[{class_xpath("os-caption-container")}]')
            is not None
        )

    def has_number(self):
        return self.has_caption() and self.get_number() != ""

    @memoize
    def get_number(self) -> str:
        caption_number = self.get_caption_elem().xpath(
            f'./*[{class_xpath("os-number")}]//text()'
        )
        return "".join(caption_number).strip()

    @memoize
    def get_caption(self) -> str:
        caption_text = self.get_caption_elem().xpath(
            f'./*[{class_xpath("os-caption")}]//text()'
        )
        return "".join(caption_text).strip()

    @memoize
    def get_title(self):
        title_text = self.get_caption_elem().xpath(
            f'./*[{class_xpath("os-title")}]//text()'
        )
        return "".join(title_text).strip()


class Figure(Captioned):
    @memoize
    def get_img(self):
        return self.xpath1(".//h:img")

    @memoize
    def get_src(self) -> str | None:
        return self.get_img().get("src")

    @memoize
    def get_alt(self) -> str | None:
        return self.get_img().get("alt")


class Table(Captioned):
    def get_title(self):
        title = super().get_title()
        if self.has_number():
            return f"Table {self.get_number()} {title}"
        else:  # pragma: no cover
            return f"Table {title}"

    def get_table_elem(self):
        return self.xpath1(".//h:table")


class Page(BookElement):
    def __init__(self, parent_chapter: "Chapter", number: str, elem):
        super().__init__(elem)
        self.parent_chapter = parent_chapter
        self.number = number

    @memoize
    def get_learning_objectives(self):
        sections = self.xpath(".//h:section")
        if sections:
            lis = sections[0].xpath(
                ".//h:li", namespaces={"h": "http://www.w3.org/1999/xhtml"}
            )
            learning_objectives = [
                "".join(li.xpath(".//text()")) for li in lis
            ]
        else:
            learning_objectives = []
        return learning_objectives

    @memoize
    def get_figures(self):
        figure_elems = self.xpath(".//h:figure/parent::*")
        return [Figure(elem) for elem in figure_elems]

    def get_number(self):
        return f"{self.parent_chapter.get_number()}.{self.number}"

    @memoize
    def get_tables(self):
        # Get all tables that are not nested in other tables
        table_elems = self.xpath(
            ".//h:table[not(ancestor::h:table)]/parent::*"
        )
        return [Table(elem) for elem in table_elems]

    @property
    def is_introduction(self):
        return self.get_title().lower() == "introduction"

    @property
    def is_summary(self):
        return self.get_title().lower().endswith("summary")


class Chapter(BookElement):
    def __init__(self, number, elem):
        super().__init__(elem)
        self.number = number

    def get_number(self):
        return self.number

    @memoize
    def get_pages(self):
        page_elems = self.xpath('.//*[@data-type="page"]')
        pages = enumerate(page_elems, start=1)
        return [Page(self, str(i), elem) for i, elem in pages]

    @memoize
    def get_chapter_outline(
        self, *, include_introduction=False, include_summary=False
    ):
        pages = self.get_pages()
        if not include_summary:
            pages = (page for page in pages if not page.is_summary)
        if not include_introduction:
            pages = (page for page in pages if not page.is_introduction)
        titles = (page.get_title().strip() for page in pages)
        non_empty_titles = (title for title in titles if title)
        return list(non_empty_titles)

    def __str__(self):
        return f"Chapter {self.get_number()} {self.get_title()}"


class Book(Element):
    @memoize
    def get_chapters(self):
        chapters = enumerate(self.xpath('//*[@data-type="chapter"]'), start=1)
        return [Chapter(str(i), el) for i, el in chapters]

    @memoize
    def get_title(self):
        title_text = self.xpath(".//h:title//text()")
        return "".join(title_text)


def get_document_indices(elems: Iterable[Element]):
    elem_list = list(elems)
    tree = elem_list[0].element.getroottree()
    for idx, elem in enumerate(tree.iter()):
        found = None
        for elem_list_idx, search in enumerate(elem_list):
            if elem == search.element:
                yield idx, search
                found = elem_list_idx
                break
        if found is not None:
            del elem_list[found]
            if not elem_list:
                return


def sort_by_document_index(elems: Iterable[Element]):
    return (elem for _, elem in get_document_indices(elems))


@dataclass(kw_only=True)
class SlideContent:
    title: str
    notes: str | None = None


@dataclass(kw_only=True)
class OutlineSlideContent(SlideContent):
    bullets: list[str]
    heading: str | None = None
    numbered: bool = False
    number_offset: int = 1


@dataclass(kw_only=True)
class FigureSlideContent(SlideContent):
    src: str
    alt: str
    caption: str


@dataclass(kw_only=True)
class TableSlideContent(SlideContent):
    html: etree.ElementBase


def chunk_bullets(bullets: list[str], max_bullets: int, max_characters: int):
    character_count = 0
    buffer = []
    avg_line_length = sum(len(b) for b in bullets) / len(bullets)
    for bullet in bullets:
        bullet_len = len(bullet)
        bullet_len *= bullet_len / avg_line_length
        if buffer and (
            len(buffer) >= max_bullets or
            character_count + bullet_len >= max_characters
        ):
            yield buffer
            buffer = [bullet]
            character_count = bullet_len
        else:
            buffer.append(bullet)
            character_count += bullet_len
    if buffer:
        yield buffer


def split_large_bullet_lists(slide_contents: Iterable[SlideContent]):
    for slide_content in slide_contents:
        if isinstance(slide_content, OutlineSlideContent):
            if slide_content.heading is not None:
                max_bullets, max_chars = 6, 300
            else:
                max_bullets, max_chars = 9, 400
            bullet_groups = list(
                chunk_bullets(slide_content.bullets, max_bullets, max_chars)
            )
            slide_count = len(bullet_groups)
            if slide_count > 1:
                number_offset = 1
                for i, bullets in enumerate(bullet_groups, start=1):
                    title = f"{slide_content.title} ({i} of {slide_count})"
                    yield OutlineSlideContent(
                        title=title,
                        heading=slide_content.heading,
                        bullets=bullets,
                        numbered=slide_content.numbered,
                        number_offset=number_offset,
                    )
                    number_offset += len(bullets)
                continue
        # Default to yielding original content
        yield slide_content


def handle_nested_tables(slide_contents: Iterable[SlideContent]):
    for slide_content in slide_contents:
        if isinstance(slide_content, TableSlideContent):
            table = slide_content
            nested_tables = table.html.xpath(
                ".//h:table", namespaces={"h": "http://www.w3.org/1999/xhtml"}
            )
            if nested_tables:
                title = slide_content.title
                tables = [table.html] + nested_tables
                count = len(tables)
                for i, tbl in enumerate(tables, start=1):
                    yield TableSlideContent(
                        title=f"{title} ({i} of {count})", html=tbl
                    )
                continue
        # Default to yielding original content
        yield slide_content


def chapter_to_slide_contents(chapter: Chapter):
    if chapter.get_chapter_outline():
        yield OutlineSlideContent(
            title="Chapter outline",
            bullets=chapter.get_chapter_outline(),
            numbered=True,
        )
    for page in chapter.get_pages():
        learning_objectives = page.get_learning_objectives()
        figures = page.get_figures()
        tables = page.get_tables()
        page_contents = figures + tables
        if learning_objectives:
            title_parts = (
                p
                for p in (page.get_number(), page.get_title())
                if p is not None
            )
            if page.is_summary:  # pragma: no cover
                heading = None
            else:
                heading = "Learning Objectives"
            yield OutlineSlideContent(
                title=" ".join(title_parts),
                heading=heading,
                bullets=learning_objectives,
            )
        if page_contents:
            for page_content in sort_by_document_index(page_contents):
                if isinstance(page_content, Figure):
                    fig = page_content
                    if not fig.has_number():
                        continue
                    src = fig.get_src()
                    alt = fig.get_alt()
                    title = f"Figure {fig.get_number()}"
                    caption = fig.get_caption() or fig.get_alt() or "None"
                    assert src, f"Missing src attribute: {title}"
                    assert alt, f"Missing alt text: {title}"
                    yield FigureSlideContent(
                        title=title,
                        src=src,
                        caption=caption,
                        alt=alt,
                        notes=alt,
                    )
                elif isinstance(page_content, Table):
                    table = page_content
                    if not table.has_number():  # pragma: no cover
                        continue
                    yield TableSlideContent(
                        title=table.get_title(), html=table.get_table_elem()
                    )


def slide_contents_to_html(
    title: str, subtitle: str, slide_contents: Iterable[SlideContent]
):
    namespace = "http://www.w3.org/1999/xhtml"
    E = ElementMaker(namespace=namespace, nsmap={None: namespace})

    def slide_content_to_html_parts(slide_contents: Iterable[SlideContent]):
        for slide_content in slide_contents:
            if isinstance(slide_content, (OutlineSlideContent,)):
                yield E.h2(slide_content.title)
                if slide_content.heading is not None:
                    yield E.strong(slide_content.heading)
                list_items = [E.li(item) for item in slide_content.bullets]
                if slide_content.numbered:
                    yield E.ol(
                        *list_items, start=str(slide_content.number_offset)
                    )
                else:
                    yield E.ul(*list_items)
            elif isinstance(slide_content, FigureSlideContent):
                yield E.h2(slide_content.title)
                yield E.figure(
                    E.img(
                        src=slide_content.src,
                        alt=slide_content.caption,
                        title=slide_content.alt,
                    )
                )
            elif isinstance(slide_content, TableSlideContent):
                yield E.h2(slide_content.title)
                yield slide_content.html
            else:  # pragma: no cover
                raise TypeError(
                    f"Unknown slide content type: {type(slide_content)}"
                )
            if slide_content.notes is not None:
                notes = slide_content.notes
                html_notes = [E.div(note) for note in notes.split("\n")]
                yield E.div(*html_notes, **{"class": "notes"})

    return E.html(
        E.head(E.title(title), E.meta(name="subtitle", content=subtitle)),
        E.body(*slide_content_to_html_parts(slide_contents)),
    )


def slides_etree_to_ppt(
    slides_etree, html_output, ppt_output, resource_dir, reference_doc
):  # pragma: no cover
    with open(html_output, "wb") as fout:
        slides_etree.getroottree().write(
            fout,
            encoding="utf-8",
            xml_declaration=False,
            pretty_print=True,
        )
    cmd = shlex.split(
        "pandoc "
        "--fail-if-warnings "
        "--from=html "
        "--to=pptx "
        f'--resource-path "{resource_dir}" '
        f'--reference-doc "{reference_doc}" '
        f'--output "{ppt_output}" '
        f'"{html_output}" '
    )
    subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)


def get_descr(shape: BaseShape):
    matches = shape.element.xpath("//*[@descr]")
    assert len(matches) == 1, "Expected only one descr"
    return matches[0]


def get_alt_text(shape: BaseShape):
    elem = get_descr(shape)
    return elem.get("descr")


def set_alt_text(shape: BaseShape, alt_text: str):
    elem = get_descr(shape)
    elem.set("descr", alt_text)


def insert_cover_image(pres: pptx.Presentation, cover_image: str):
    height = pptx.util.Inches(3.5)
    pic = pres.slides[0].shapes.add_picture(
        cover_image,
        height=height,
        top=round(pres.slide_height * 5 / 7 - height / 2),
        left=0,
    )
    pic.left = round(pres.slide_width / 2 - pic.width / 2)
    pic.name = "Cover Image"
    set_alt_text(pic, "Cover image")


def fix_image_alt_text(slides: Iterable[Slide]):
    for slide in slides:
        for shape in slide.shapes:
            if isinstance(shape, Picture):
                alt_text = get_alt_text(shape)
                # Remove image path from alt text because otherwise powerpoint
                # does not recognize the alt text as existing
                alt_text_no_image_path = re.sub(
                    r"\s*\.{1,2}\/[^.]+\.[a-z]+$",
                    "",
                    alt_text,
                    flags=re.IGNORECASE,
                )
                set_alt_text(shape, alt_text_no_image_path)
        yield slide


def adjust_figure_caption_font(slides: Iterable[Slide]):
    for slide in slides:
        if slide.shapes.title.text.lower().startswith("figure"):
            caption = slide.shapes[-1]
            for p in caption.text_frame.paragraphs:
                p.font.size = pptx.util.Pt(12)
        yield slide


def slides_post_process(pres: pptx.Presentation):
    slides = pres.slides
    slides = fix_image_alt_text(slides)
    slides = adjust_figure_caption_font(slides)
    _ = list(slides)  # Run generator to completion
    slide_layouts_by_name = {sl.name: sl for sl in pres.slide_layouts}
    last_slide_layout = slide_layouts_by_name["Last Slide"]
    pres.slides.add_slide(last_slide_layout)


def fix_namespaces(tree):
    # These are tag names mapped to namespaces that pandoc fails to add when
    # converting to pptx. Normally lxml would resolve namespace prefixes to the
    # namespace. Since these tags use undefined prefixes, they are not resolved
    ns_fixes = {
        "a14:m": etree.QName(
            "http://schemas.microsoft.com/office/drawing/2010/main", "m"
        ),
    }
    for elem in tree.iter():
        if elem.tag in ns_fixes:
            qname = ns_fixes[elem.tag]
            nsname = elem.tag.split(":")[0]
            new_elem = etree.Element(
                qname, nsmap={nsname: qname.namespace}, attrib=elem.attrib
            )
            for child in elem.iterchildren():
                new_elem.append(child)
            parent = elem.getparent()
            parent.replace(elem, new_elem)


def is_slide_filename(filename):
    return re.match(r".+slides/slide\d+\.xml$", filename) is not None


def fix_pptx_file(input_path: Path):  # pragma: no cover
    lax_xml_parser = etree.XMLParser(recover=True)
    output_path = input_path.with_suffix(".tmp")
    with (
        ZipFile(input_path) as pptx_i,
        ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as pptx_o,
    ):
        for info in pptx_i.infolist():
            with (
                pptx_i.open(info.filename, "r") as fin,
                pptx_o.open(info.filename, "w") as fout,
            ):
                content = fin.read()
                if is_slide_filename(info.filename):
                    xml = etree.XML(content, lax_xml_parser)
                    fix_namespaces(xml)
                    xml.getroottree().write(fout)
                else:
                    fout.write(content)
    output_path.rename(input_path)


def main():
    book_input = Path(sys.argv[1]).resolve(strict=True)
    resource_dir = Path(sys.argv[2]).resolve(strict=True)
    reference_doc = Path(sys.argv[3]).resolve(strict=True)
    cover_image = Path(sys.argv[4]).resolve()
    out_fmt = sys.argv[5]
    tree = etree.parse(str(book_input), None)
    book = Book(tree)
    for chapter in book.get_chapters():
        print(f"Working on: {chapter}", file=sys.stderr)
        title = f"{chapter.get_number()} {chapter.get_title()}".replace("'", "")
        slug = slugify(title)
        ppt_output, html_output = (
            Path(out_fmt.format(slug=slug, extension="pptx")),
            Path(out_fmt.format(slug=slug, extension="html")),
        )
        slide_contents = chapter_to_slide_contents(chapter)
        slide_contents = split_large_bullet_lists(slide_contents)
        slide_contents = handle_nested_tables(slide_contents)
        slides_etree = slide_contents_to_html(
            book.get_title(),
            f"Chapter {chapter.get_number()} {chapter.get_title()}",
            slide_contents,
        )
        slides_etree_to_ppt(
            slides_etree, html_output, ppt_output, resource_dir, reference_doc
        )
        fix_pptx_file(ppt_output)
        tmp_path = Path(ppt_output).with_suffix(".pptx.tmp")
        pres = pptx.Presentation(ppt_output)
        slides_post_process(pres)
        if cover_image.exists():
            insert_cover_image(pres, str(cover_image))
        pres.save(str(tmp_path))
        tmp_path.rename(ppt_output)
