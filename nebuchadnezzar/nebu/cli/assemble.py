from pathlib import Path

import click

from ..formatters import (assemble_collection, fetch_insert_includes,
                          interactive_callback_factory, resolve_module_links,
                          update_ids)
from ..models.book_part import BookPart
from ..xml_utils import fix_namespaces
from ._common import common_params

ASSEMBLED_FILENAME = "collection.assembled.xhtml"
DEFAULT_INTERACTIVES_PATH = "interactives"


def create_interactive_factories(interactives_root):
    exercise_match_paths = (
        (
            "{INTERACTIVES_ROOT}",
            "{}{{itemCode}}".format(
                interactives_root
            ),
        ),
    )
    return [
        interactive_callback_factory(exercise_match, exercise_path)
        for exercise_match, exercise_path in exercise_match_paths
    ]


def collection_to_assembled_xhtml(
    collection, docs_by_id, docs_by_uuid, input_dir, interactives_path
):
    page_uuids = list(docs_by_uuid.keys())
    includes = create_interactive_factories(interactives_path)
    # Use docs_by_uuid.values to ensure each document is only used one time
    for document in docs_by_uuid.values():
        # Step 1: Rewrite module links
        resolve_module_links(document, docs_by_id, input_dir)
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
    "--interactives-path",
    default=DEFAULT_INTERACTIVES_PATH,
    help="Default {}".format(DEFAULT_INTERACTIVES_PATH),
)
@click.pass_context
def assemble(ctx, input_dir, output_dir, interactives_path):
    """Assembles litezip structure data into a single-page-html file.

    This also stores the intermediary results alongside the resulting
    assembled single-page-html.

    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_assembled_xhtml = output_dir / ASSEMBLED_FILENAME

    if output_assembled_xhtml.exists():
        confirm_msg = (
            "File '{}' already exists. Would you like to replace it?".format(
                output_assembled_xhtml
            )
        )
        click.confirm(confirm_msg, abort=True, err=True)
        output_assembled_xhtml.unlink()
    if not output_dir.exists():
        output_dir.mkdir()

    collection, docs_by_id, docs_by_uuid = BookPart.collection_from_file(
        input_dir / "collection.xml"
    )
    assembled_xhtml = collection_to_assembled_xhtml(
        collection,
        docs_by_id,
        docs_by_uuid,
        input_dir,
        interactives_path
    )
    output_assembled_xhtml.write_bytes(assembled_xhtml)

    return 0
