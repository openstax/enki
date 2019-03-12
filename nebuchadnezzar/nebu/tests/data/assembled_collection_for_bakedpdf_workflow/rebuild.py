""" This script rebuilds the contents of this directory """
from pathlib import Path

from cnxepub import formatters
from nebu.models.binder import Binder
from nebu.models.document import Document
from nebu.tests.models.test_document import mock_reference_resolver
from nebu.utils import relative_path


input_dir = Path('../collection_for_bakedpdf_workflow')
output_dir = Path('.')


def main():
    # Transform the modules from cnxml to html
    for id in ('m46882', 'm46909', 'm46913'):
        filepath = input_dir / id / 'index.cnxml'
        doc = Document.from_index_cnxml(filepath, mock_reference_resolver)

        # Write the html to file
        html_filepath = (output_dir / '{}.xhtml'.format(id))
        html_filepath.unlink()
        with html_filepath.open('wb') as fb:
            fb.write(bytes(formatters.HTMLFormatter(doc)))

        # Create a symbolic link back to the module's source directory
        link_to_source_dir = output_dir / id
        link_to_source_dir.unlink()
        source_dir = input_dir / id
        link_to_source_dir.symlink_to(relative_path(source_dir, output_dir))

    # Create the single-page-html
    binder = Binder.from_collection_xml(input_dir / 'collection.xml')
    with (output_dir / 'collection.assembled.xhtml').open('wb') as fb:
        fb.write(bytes(formatters.SingleHTMLFormatter(binder)))


if __name__ == '__main__':
    main()
