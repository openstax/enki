from pathlib import Path

import click
from cnxepub.formatters import (
    HTMLFormatter,
    SingleHTMLFormatter,
    exercise_callback_factory,
)
from cnxepub.models import flatten_to_documents

from ._common import common_params, logger
from ..models.binder import Binder
from ..models.utils import scan_for_id_mapping, scan_for_uuid_mapping
from ..utils import relative_path


ASSEMBLED_FILENAME = 'collection.assembled.xhtml'
DEFAULT_EXERCISES_HOST = 'exercises.openstax.org'


def produce_collection_xhtml(binder, output_dir, includes):
    collection_xhtml = output_dir / ASSEMBLED_FILENAME
    with collection_xhtml.open('wb') as fb:
        fb.write(bytes(SingleHTMLFormatter(binder, includes, threads=20)))

    return collection_xhtml


def provide_supporting_files(input_dir, output_dir, binder):
    documents = {doc.id: doc for doc in flatten_to_documents(binder)}
    id_to_filepath_mapping = scan_for_id_mapping(input_dir)
    id_to_filepath_mapping.update(scan_for_uuid_mapping(input_dir))
    for id, filepath in id_to_filepath_mapping.items():
        if id in documents:
            if (output_dir / id).exists():
                (output_dir / id).unlink()
            (output_dir / id).symlink_to(
                relative_path(filepath.parent, output_dir)
            )
            with (output_dir / '{}.xhtml'.format(id)).open('wb') as fb:
                fb.write(bytes(HTMLFormatter(documents[id])))


@click.command(name='assemble')
@common_params
@click.argument('input-dir', type=click.Path(exists=True))
@click.argument('output-dir', type=click.Path())
@click.option('--exercise-token',
              help='Token for including answers in exercises')
@click.option('--exercise-host', default=DEFAULT_EXERCISES_HOST,
              help='Default {}'.format(DEFAULT_EXERCISES_HOST))
@click.pass_context
def assemble(ctx, input_dir, output_dir, exercise_token, exercise_host):
    """Assembles litezip structure data into a single-page-html file.

    This also stores the intermediary results alongside the resulting
    assembled single-page-html.

    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    collection_assembled_xhtml = (output_dir / ASSEMBLED_FILENAME)

    if collection_assembled_xhtml.exists():
        confirm_msg = (
            "File '{}' already exists. Would you like to replace it?"
            .format(collection_assembled_xhtml)
        )
        click.confirm(confirm_msg, abort=True, err=True)
        collection_assembled_xhtml.unlink()
    if not output_dir.exists():
        output_dir.mkdir()

    collection_xml = input_dir / 'collection.xml'
    binder = Binder.from_collection_xml(collection_xml)

    # Write the collection.xml symlink to the output directory
    output_collection_xml = (output_dir / 'collection.xml')
    if output_collection_xml.exists():
        output_collection_xml.unlink()
    output_collection_xml.symlink_to(
        relative_path(collection_xml, output_dir)
    )

    # Fetch exercises as part of producing the collection xhtml
    exercise_match_urls = (
        ('#ost/api/ex/',
         'https://{}/api/exercises?q=tag:{{itemCode}}'.format(exercise_host)),
        ('#exercise/',
         'https://{}/api/exercises?q=nickname:{{itemCode}}'.format(
             exercise_host)),
    )
    includes = [exercise_callback_factory(
        exercise_match, exercise_url, token=exercise_token)
        for exercise_match, exercise_url in exercise_match_urls]

    # Write the binder out as a single-page-html
    collection_xhtml = produce_collection_xhtml(binder, output_dir, includes)
    logger.debug('Wrote: {}'.format(str(collection_xhtml.resolve())))

    # Write the symbolic links for modules to the output directory
    provide_supporting_files(input_dir, output_dir, binder)

    return 0
