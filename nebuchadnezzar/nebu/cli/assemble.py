from pathlib import Path

import click

from ._common import common_params
from ..models.book_part import BookPart
from ..formatters import (
    fetch_insert_includes,
    resolve_module_links,
    update_ids,
    assemble_collection,
    exercise_callback_factory,
)
from ..xml_utils import fix_namespaces
from ..models.book_container import BookContainer
from ..models.path_resolver import PathResolver


ASSEMBLED_FILENAME = "collection.assembled.xhtml"
DEFAULT_EXERCISES_HOST = "exercises.openstax.org"


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


def collection_to_assembled_xhtml(
    collection, docs_by_id, docs_by_uuid, path_resolver, token, exercise_host
):
    page_uuids = list(docs_by_uuid.keys())
    includes = create_exercise_factories(exercise_host, token)
    # Use docs_by_uuid.values to ensure each document is only used one time
    for document in docs_by_uuid.values():
        # Step 1: Rewrite module links
        resolve_module_links(document, docs_by_id, path_resolver)
        # Step 2: Update ids and links
        update_ids(document)

    # Combine all the pieces together into the final assembled document
    assembled_collection = assemble_collection(collection)

    # Finally, fetch and insert any includes from remote sources
    fetch_insert_includes(assembled_collection, page_uuids, includes)

    return fix_namespaces(assembled_collection)


@click.command(name="assemble")
@common_params
@click.argument("input-dir", type=click.Path(exists=True))
@click.argument("output-dir", type=click.Path())
@click.option(
    "--exercise-token", help="Token for including answers in exercises"
)
@click.option(
    "--exercise-host",
    default=DEFAULT_EXERCISES_HOST,
    help="Default {}".format(DEFAULT_EXERCISES_HOST),
)
@click.pass_context
def assemble(ctx, input_dir, output_dir, exercise_token, exercise_host):
    """Assembles litezip structure data into a single-page-html file.

    This also stores the intermediary results alongside the resulting
    assembled single-page-html.

    """
    books_xml = Path(input_dir) / "META-INF" / "books.xml"
    container = BookContainer.from_str(books_xml.read_text(), input_dir)
    path_resolver = PathResolver(container)
    output_dir = Path(output_dir)
    if not output_dir.exists():
        output_dir.mkdir()

    for book in container.books:
        output_assembled_xhtml = output_dir / f"{book.slug}.assembled.xhtml"

        assert not output_assembled_xhtml.exists(), \
            f'File "{output_assembled_xhtml}" already exists.'

        collection, docs_by_id, docs_by_uuid = BookPart.collection_from_file(
            path_resolver.get_collection_path(book.slug),
            path_resolver
        )
        assembled_xhtml = collection_to_assembled_xhtml(
            collection,
            docs_by_id,
            docs_by_uuid,
            path_resolver,
            exercise_token,
            exercise_host,
        )
        output_assembled_xhtml.write_bytes(assembled_xhtml)

    return 0
