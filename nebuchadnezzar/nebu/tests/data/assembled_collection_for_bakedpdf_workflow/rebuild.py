""" This script rebuilds the contents of this directory """
import os.path
from pathlib import Path

from cnxepub import formatters
from nebu.models.document import Document
from nebu.tests.models.test_document import mock_reference_resolver

input_dir = Path('../collection_for_bakedpdf_workflow')
output_dir = Path('.')


def relative_path(path, start=Path('.')):
    return Path(os.path.relpath(str(path.resolve()), start=str(start)))


def main():
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


if __name__ == '__main__':
    main()
