from pathlib import Path
import json

import click

from ._common import common_params
from ..utils import re_first_or_default
from ..models.book_container import BookContainer
from ..models.path_resolver import PathResolver



@click.command(name="parse-repo")
@common_params
@click.argument("input-dir", type=click.Path(exists=True))
def parse_repo(input_dir):
    books_xml = Path(input_dir) / "META-INF" / "books.xml"
    container = BookContainer.from_str(books_xml.read_bytes(), input_dir)
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )
    combined = {
        "container": container,
        "modules": path_resolver.module_paths_by_id,
        "collections": path_resolver.collection_paths_by_book
    }
    print(json.dumps(combined, indent=2, default=lambda o: o.__dict__))
