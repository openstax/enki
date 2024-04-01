import os
from pathlib import Path
import shutil
import json
from functools import lru_cache

import click

from ._common import common_params
from ..models.book_part import BookPart
from ..formatters import (
    exercise_callback_factory,
    insert_includes,
    resolve_module_links,
    update_ids,
    assemble_collection,
    interactive_callback_factory,
)
from ..xml_utils import fix_namespaces
from ..utils import re_first_or_default, unknown_progress
from ..models.book_container import BookContainer
from ..models.path_resolver import PathResolver
from ..media_utils import get_media_metadata


DEFAULT_EXERCISES_HOST = "exercises.openstax.org"


def create_interactive_factories(
        path_resolver: PathResolver, docs_by_id, media_handler
):
    return [
        interactive_callback_factory(
            "{INTERACTIVES_ROOT}",
            path_resolver,
            docs_by_id,
            media_handler,
        )
    ]


def create_exercise_factories(exercise_host, token):
    exercise_match_urls = (
        (
            "#ost/api/ex/",
            "https://{}/api/exercises?q=tag:{{itemCode}}".format(
                exercise_host
            ),
        ),
        (
            "#exercise/",
            "https://{}/api/exercises?q=nickname:{{itemCode}}".format(
                exercise_host
            ),
        ),
    )
    return [
        exercise_callback_factory(exercise_match, exercise_url, token=token)
        for exercise_match, exercise_url in exercise_match_urls
    ]


def save_resource_metadata(metadata, resource_dir, filename):
    assert not filename.endswith(".json"), "Duplicate .json suffix"
    with open(os.path.join(resource_dir, f"{filename}.json"), "w") as fout:
        json.dump(metadata, fout)


def to_dom_resource_path(filename):
    return f"../resources/{filename}"


def h5p_media_handler_factory(path_resolver: PathResolver, resource_dir: str):
    @lru_cache
    def handle_resource(
        interactive_id: str, resource_orig_path: str, is_image: bool
    ):
        resource_abs_path = path_resolver.find_interactives_path(
            interactive_id, resource_orig_path
        )
        assert resource_abs_path is not None, \
            f"Could not find resource: {interactive_id}:{resource_orig_path}"
        sha1, metadata = get_media_metadata(resource_abs_path, is_image)
        resource_dst = os.path.join(resource_dir, sha1)
        shutil.move(resource_abs_path, resource_dst)
        save_resource_metadata(metadata, resource_dir, sha1)
        return to_dom_resource_path(sha1)

    def h5p_media_handler(interactive_id, elem, uri_attrib, is_image):
        resource_orig_path = elem.attrib[uri_attrib]
        elem.attrib[uri_attrib] = handle_resource(
            interactive_id, resource_orig_path, is_image
        )
    return h5p_media_handler


def collection_to_assembled_xhtml(
    collection,
    docs_by_id,
    docs_by_uuid,
    path_resolver,
    token,
    exercise_host,
    resource_dir
):
    page_uuids = list(docs_by_uuid.keys())
    includes = (
        create_interactive_factories(
            path_resolver,
            docs_by_id,
            h5p_media_handler_factory(path_resolver, resource_dir)
        ) +
        create_exercise_factories(exercise_host, token)
    )
    # Use docs_by_uuid.values to ensure each document is only used one time
    with unknown_progress("Resolving document references"):
        for document in docs_by_uuid.values():
            # Step 1: Rewrite module links
            resolve_module_links(document, docs_by_id, path_resolver)
            # Step 2: Update ids and links
            update_ids(document)

    with unknown_progress("Combining documents"):
        # Combine all the pieces together into the final assembled document
        assembled_collection = assemble_collection(collection)

    with unknown_progress("Fetching and inserting exercises"):
        # Finally, fetch and insert any includes from remote sources
        insert_includes(assembled_collection, page_uuids, includes)

    return fix_namespaces(assembled_collection)


@click.command(name="assemble")
@common_params
@click.argument("input-dir", type=click.Path(exists=True))
@click.argument("output-dir", type=click.Path())
@click.argument("resource-dir", type=click.Path())
@click.option(
    "--exercise-token", help="Token for including answers in exercises"
)
@click.option(
    "--exercise-host",
    default=DEFAULT_EXERCISES_HOST,
    help="Default {}".format(DEFAULT_EXERCISES_HOST),
)
@click.pass_context
def assemble(
    ctx,
    input_dir,
    output_dir,
    resource_dir,
    exercise_token,
    exercise_host
):
    """Assembles litezip structure data into a single-page-html file.

    This also stores the intermediary results alongside the resulting
    assembled single-page-html.

    """
    books_xml = Path(input_dir) / "META-INF" / "books.xml"
    container = BookContainer.from_str(books_xml.read_bytes(), input_dir)
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r'm[0-9]+', s),
    )
    output_dir = Path(output_dir)
    if not output_dir.exists():
        output_dir.mkdir()

    for book in container.books:
        output_assembled_xhtml = output_dir / f"{book.slug}.assembled.xhtml"

        assert not output_assembled_xhtml.exists(), \
            f'File "{output_assembled_xhtml}" already exists.'

        with unknown_progress(f"Assembling {book.slug}"):
            (
                collection,
                docs_by_id,
                docs_by_uuid,
            ) = BookPart.collection_from_file(
                path_resolver.get_collection_path(book.slug), path_resolver
            )
            assembled_xhtml = collection_to_assembled_xhtml(
                collection,
                docs_by_id,
                docs_by_uuid,
                path_resolver,
                exercise_token,
                exercise_host,
                resource_dir
            )
            output_assembled_xhtml.write_bytes(assembled_xhtml)

    return 0
