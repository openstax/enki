import sys
import os
from pathlib import Path
import shutil

from lxml import etree
from lxml.html import XHTMLParser


def copy_with_deps(src_path: Path, src_root: Path, dst_root: Path):
    query = (
        '//*[@src][not(starts-with(@src, "http"))]/@src | '
        '//*[local-name()="link"][@href][not(starts-with(@href,"http"))]/@href'
    )
    if src_path.is_file() and src_path.suffix.lower() in (".html", ".xhtml"):
        doc_path = src_path.parent
        tree = etree.parse(src_path, parser=XHTMLParser(recover=True))
        src_values = tree.xpath(query)
        for src in src_values:
            src = src.strip().lstrip(os.sep)
            resolved_path = (doc_path / src).resolve()
            if src and resolved_path.exists():
                copy_with_deps(resolved_path, src_root, dst_root)
        src_path = doc_path
    dst = dst_root / src_path.relative_to(src_root)
    dst.parent.mkdir(exist_ok=True, parents=True)
    print(f"{src_path} -> {dst}", file=sys.stderr)
    if src_path.is_dir():
        shutil.copytree(src_path, dst, copy_function=shutil.copy2, dirs_exist_ok=True)
    else:
        shutil.copy2(src_path, dst)


def main():
    args = iter(sys.argv[1:])
    src = Path(next(args)).resolve(strict=True)
    src_root = Path(next(args)).resolve(strict=True)
    dst_root = Path(next(args)).resolve()
    copy_with_deps(src, src_root, dst_root)


if __name__ == "__main__":
    main()
