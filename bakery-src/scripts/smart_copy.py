import sys
import os
from pathlib import Path
import shutil

from lxml import etree
from lxml.html import XHTMLParser


def warn(msg):
    print("[WARNING]", msg, file=sys.stderr)


def get_archive_url_formatter():
    corgi_cloudfront_url = os.getenv("CORGI_CLOUDFRONT_URL")
    code_version = os.getenv("CODE_VERSION")
    if not code_version:
        warn("Assuming we are running on local")
        # TODO: Maybe find a way to make this work in local builds
        format_str = "./{url}"
    else:
        archive_preview = os.getenv("PREVIEW_APP_URL_PREFIX")
        assert archive_preview
        archive_preview = archive_preview.lstrip("/")
        if corgi_cloudfront_url:
            format_str = (
                f"{corgi_cloudfront_url}/{archive_preview}/{code_version}/{{url}}"
            )
        else:
            archive_base = os.getenv(
                "PREVIEW_APP_BASE_URL", "https://openstax.org"
            )
            archive_base = archive_base.rstrip("/")
            format_str = (
                f"{archive_base}/{archive_preview}/{code_version}/{{url}}"
            )

    def to_archive(url: str):
        return format_str.format(url=url)

    return to_archive


def copy_with_deps(src_path: Path, src_root: Path, dst_root: Path):
    src_query = (
        '//*[local-name()!="iframe"]/@src[not(starts-with(.,"http"))] | '
        '//*[local-name()="link"]/@href[not(starts-with(.,"http"))]'
    )
    iframe_query = (
        '//*[local-name()="iframe"][@src][not(starts-with(@src,"http"))]'
    )
    get_archive_url = get_archive_url_formatter()
    doc_path = src_path.parent
    tree = etree.parse(src_path, parser=XHTMLParser(recover=True))
    for iframe in tree.xpath(iframe_query):
        src = iframe.get("src")
        if not src or not src.startswith("../resources/"):  # pragma: no cover
            warn(f"Unexpected iframe src format: {src}")
            continue
        iframe.attrib["src"] = get_archive_url(src[3:])
    for src in tree.xpath(src_query):
        src = src.strip().lstrip("/")
        resolved_path = (doc_path / src).resolve()
        if src and resolved_path.exists():
            dst = dst_root / resolved_path.relative_to(src_root)
            dst.parent.mkdir(exist_ok=True, parents=True)
            print(f"{resolved_path} -> {dst}", file=sys.stderr)
            shutil.copy2(resolved_path, dst)
    dst_root.mkdir(exist_ok=True, parents=True)
    tree.write(str(dst_root / src_path.name), encoding="utf-8")


def main():
    args = iter(sys.argv[1:])
    src = Path(next(args)).resolve(strict=True)
    src_root = Path(next(args)).resolve(strict=True)
    dst_root = Path(next(args)).resolve()
    copy_with_deps(src, src_root, dst_root)


if __name__ == "__main__":
    main()  # pragma: no cover
