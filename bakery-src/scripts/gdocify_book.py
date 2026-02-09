"""Make modifications to page XHTML files specific to GDoc outputs
"""
import json
import re
import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, UnidentifiedImageError
from lxml import etree

from .utils import get_mime_type, patch_math_for_pandoc
from .profiler import timed
from . import excepthook


excepthook.attach(sys)

# folder where all resources are saved in checksum step
RESOURCES_FOLDER = '../resources/'
# sRGB color profile file in Debian icc-profiles-free package
SRGB_ICC = '/usr/share/color/icc/sRGB.icc'
# user installed Adobe ICC CMYK profile US Web Coated (SWOP)
USWEBCOATEDSWOP_ICC = '/usr/share/color/icc/USWebCoatedSWOP.icc'
# Namespace for xhtml
NS_XHTML = "http://www.w3.org/1999/xhtml"


@timed
def update_doc_links(doc, book_uuid, book_slugs_by_uuid):
    """Modify links in doc"""

    def _rex_url_builder(book, page, fragment):
        base_url = f"http://openstax.org/books/{book}/pages/{page}"
        if fragment:
            return f"{base_url}#{fragment}"
        else:
            return base_url

    # It's possible that all links starting with "/contents/"" are intra-book
    # and all links starting with "./" are inter-book, making the check redundant
    for node in doc.xpath(
            '//x:a[@href and starts-with(@href, "/contents/") or '
            'starts-with(@href, "./")]',
            namespaces={"x": NS_XHTML}
    ):
        # This is either an intra-book link or inter-book link. We can
        # differentiate the latter by data-book-uuid attrib).
        if node.attrib.get("data-book-uuid"):
            page_link = node.attrib["href"]
            # Link may have fragment
            page_fragment = page_link.split(
                "#")[-1] if "#" in page_link else ''

            external_book_uuid = node.attrib["data-book-uuid"]
            external_book_slug = book_slugs_by_uuid[external_book_uuid]
            external_page_slug = node.attrib["data-page-slug"]
            node.attrib["href"] = _rex_url_builder(
                external_book_slug, external_page_slug, page_fragment
            )
        else:
            book_slug = book_slugs_by_uuid[book_uuid]
            page_slug = node.attrib["data-page-slug"]
            page_fragment = node.attrib["data-page-fragment"]
            node.attrib["href"] = _rex_url_builder(
                book_slug, page_slug, page_fragment
            )


@timed
def linkify_figures(doc):
    figures = doc.xpath('//x:figure', namespaces={"x": NS_XHTML})
    for node in figures:
        figure_id = node.get("id")
        if figure_id:
            span = etree.Element(f"{{{NS_XHTML}}}span")
            span.set("id", figure_id)
            del node.attrib["id"]
            node.insert(0, span)


@timed
def fix_headings(doc):
    heading_nodes = []
    min_level = 7

    for node in doc.iter():
        tag = node.tag

        if not isinstance(tag, str):
            continue

        tag = etree.QName(tag).localname
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            heading_nodes.append((node, level))
            min_level = min(min_level, level)

    # If there's already an h1 or no headings, nothing to do
    if min_level <= 1 or min_level == 7:
        return

    # NOTE: Assumes headings are already in the correct order
    shift = min_level - 1
    for node, level in heading_nodes:
        new_level = level - shift
        new_tag = f"{{{NS_XHTML}}}h{new_level}"
        node.tag = new_tag


def remove_iframes(doc):
    for node in doc.xpath('//x:iframe', namespaces={"x": NS_XHTML}):
        node.getparent().remove(node)


def _convert_cmyk2rgb_embedded_profile(img_filename):
    """ImageMagick commandline to convert from CMYK with
    an existing embedded icc profile"""
    # mogrify -profile sRGB.icc +profile '*' picture.jpg
    return f'mogrify -profile "{SRGB_ICC}" +profile \'*\' "{img_filename}"'  # pragma: no cover


def _convert_cmyk2rgb_no_profile(img_filename):
    """ImageMagick commandline to convert from CMYK without any
    embedded icc profile"""
    # mogrify -profile USWebCoatedSWOP.icc -profile sRGB.icc +profile '*' picture.jpg
    return (f'mogrify -profile "{USWEBCOATEDSWOP_ICC}" -profile "{SRGB_ICC}"'
            f' +profile \'*\' "{img_filename}"')  # pragma: no cover


def _universal_convert_rgb_command(img_filename):
    """ImageMagick commandline to convert an unknown color profile to RGB.
    Warning: Probably does not work perfectly color accurate."""
    return f'mogrify -colorspace sRGB -type truecolor "{img_filename}"'  # pragma: no cover


@timed
async def fix_jpeg_colorspace(img_filename):
    """Searches for JPEG image resources which are encoded in colorspace
    other than RGB or Greyscale and convert them to RGB"""
    if img_filename.is_file():
        mime_type = get_mime_type(str(img_filename))

        # Only check colorspace of JPEGs (GIF, PNG etc. don't have breaking colorspaces)
        if mime_type == 'image/jpeg':
            try:
                im = Image.open(str(img_filename))
                # https://pillow.readthedocs.io/en/stable/handbook/concepts.html#modes
                colorspace = im.mode
                im.close()
                if not re.match(r"^RGB.*", colorspace):  # pragma: no cover
                    if colorspace != '1' and not re.match(r"^L\w?", colorspace):
                        # here we have a color space like CMYK or YCbCr most likely
                        # decide which command line to use
                        if colorspace == 'CMYK':
                            with TemporaryDirectory() as temp_dir:
                                profile = Path(temp_dir) / Path('embedded.icc')
                                # save embedded profile if existing
                                extractembedded = await asyncio.create_subprocess_shell(
                                    f'convert "{img_filename}" "{profile}"',
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE)
                                stdout, stderr = await extractembedded.communicate()
                                # was there an embedded icc profile?
                                if extractembedded.returncode == 0 and \
                                        profile.is_file() and \
                                        profile.stat().st_size > 0:
                                    cmd = _convert_cmyk2rgb_embedded_profile(
                                        img_filename)
                                    print('Convert CMYK (embedded) to '
                                          'RGB: {}'.format(img_filename))
                                else:
                                    cmd = _convert_cmyk2rgb_no_profile(
                                        img_filename)
                                    print('Convert CMYK (no profile) to '
                                          'RGB: {}'.format(img_filename))
                                if profile.is_file():
                                    profile.unlink()  # delete file
                        else:
                            cmd = _universal_convert_rgb_command(img_filename)
                            print('Warning: Convert exceptional color '
                                  'space {} to RGB: {}'.format(colorspace, img_filename))
                        # convert command itself
                        fconvert = await asyncio.create_subprocess_shell(
                            cmd, stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE)
                        stdout, stderr = await fconvert.communicate()
                        if fconvert.returncode != 0:
                            raise Exception('Error converting file {}'.format(img_filename) +
                                            ' to RGB color space: {}'.format(stderr))
            except UnidentifiedImageError:  # pragma: no cover
                # do nothing if we cannot open the image
                print('Warning: Could not parse JPEG image with PIL: ' +
                      str(img_filename))
    else:
        raise Exception('Error: Resource file not existing: ' +
                        str(img_filename))  # pragma: no cover


class AsyncJobQueue:
    def __init__(self, worker_count, qsize=None):
        self.worker_count = worker_count
        self.queue = (asyncio.Queue(qsize) if qsize is not None
                      else asyncio.Queue())
        self.workers = []

    @timed
    async def __aenter__(self):
        async def worker(queue):
            while True:
                try:
                    job = await queue.get()
                    await job
                    queue.task_done()
                except Exception as e:  # pragma: no cover
                    # No way to communicate the error back at the moment
                    sys.exit(e)
        self.workers = [asyncio.create_task(worker(self.queue))
                        for _ in range(self.worker_count)]
        return self.queue

    @timed
    async def __aexit__(self, *_):
        await self.queue.join()
        for worker in self.workers:
            worker.cancel()


@timed
def get_img_resources(doc, out_dir):
    """Iterates over all image resources--absolute paths--in the document"""

    # get all img resources from img and a nodes
    # assuming all resources from checksum step are in the same folder
    img_xpath = '//x:img[@src and starts-with(@src, "{0}")]/@src' \
                '|' \
                '//x:a[@href and starts-with(@href, "{0}")]/@href'.format(
                    RESOURCES_FOLDER)
    for node in doc.xpath(img_xpath, namespaces={'x': NS_XHTML}):
        img_filename = Path(node)
        img_filename = (out_dir / img_filename).resolve().absolute()
        yield img_filename


@timed
async def run_async():
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    out_dir = Path(sys.argv[2]).resolve(strict=True)
    book_slugs_file = Path(sys.argv[3]).resolve(strict=True)

    if len(sys.argv) >= 5:
        worker_count = int(sys.argv[4])
    else:  # pragma: no cover
        try:
            from multiprocessing import cpu_count
            # Some container configurations prohibit this action
            worker_count = cpu_count()
        except Exception:
            print("Error detecting cpu count, using 4 workers...")
            worker_count = 4

    # Build map of book UUIDs to slugs that can be used to construct both
    # inter-book and intra-book links
    with book_slugs_file.open() as json_file:
        json_data = json.load(json_file)
        book_slugs_by_uuid = {
            elem["uuid"]: elem["slug"] for elem in json_data
        }

    async with AsyncJobQueue(worker_count) as queue:
        queued_items = set()
        for book_uuid in book_slugs_by_uuid.keys():
            for xhtml_file in in_dir.glob(f"{book_uuid}@*.xhtml"):
                doc = etree.parse(str(xhtml_file))
                update_doc_links(
                    doc,
                    book_uuid,
                    book_slugs_by_uuid
                )
                # Disassemble puts all math into xhtml namespace
                patch_math_for_pandoc(doc, NS_XHTML)
                remove_iframes(doc)
                linkify_figures(doc)
                fix_headings(doc)
                for img_filename in get_img_resources(doc, out_dir):
                    if img_filename not in queued_items:  # pragma: no cover
                        queued_items.add(img_filename)
                        queue.put_nowait(fix_jpeg_colorspace(img_filename))
                doc.write(str(out_dir / xhtml_file.name), encoding="utf8")


@timed
def main():  # pragma: no cover
    asyncio.run(run_async())


if __name__ == "__main__":  # pragma: no cover
    main()
