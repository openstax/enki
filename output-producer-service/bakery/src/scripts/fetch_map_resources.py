"""Map resource files used in CNXML to provided path"""

import json
import re
import shutil
import sys
from pathlib import Path

from lxml import etree

from . import utils

# relative links must work both locally, on PDF, and on REX, and images are
# uploaded with the prefix 'resources/' in S3 for REX
# so the output directory name MUST be resources
RESOURCES_DIR_NAME = 'resources'


def create_json_metadata(output_dir, sha1, mime_type, s3_md5, original_name):
    """ Create json with MIME type of a (symlinked) resource file """
    data = {}
    data['original_name'] = original_name
    data['mime_type'] = mime_type
    data['s3_md5'] = s3_md5
    data['sha1'] = sha1
    json_file = output_dir / f'{sha1}.json'
    with json_file.open(mode='w') as outfile:
        json.dump(data, outfile)


def main():
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    original_resources_dir = Path(sys.argv[2]).resolve(strict=True)
    resources_parent_dir = Path(sys.argv[3]).resolve(strict=True)
    unused_resources_dump = Path(sys.argv[4]).resolve()
    resources_dir = resources_parent_dir / RESOURCES_DIR_NAME
    resources_dir.mkdir(exist_ok=True)
    unused_resources_dump.mkdir(exist_ok=True)

    cnxml_files = in_dir.glob("**/*.cnxml")

    filename_to_data = {}

    for child in original_resources_dir.glob('*'):
        if child.is_dir():
            shutil.move(str(child), str(resources_dir / child.name))

    for cnxml_file in cnxml_files:
        doc = etree.parse(str(cnxml_file))
        for node in doc.xpath(
                '//x:image',
                namespaces={"x": "http://cnx.rice.edu/cnxml"}
        ):
            resource_original_src = node.attrib["src"]
            resource_original_filepath = \
                (cnxml_file.parent / resource_original_src).resolve()

            sha1, s3_md5 = utils.get_checksums(
                str(resource_original_filepath)
            )
            mime_type = utils.get_mime_type(str(resource_original_filepath))

            if sha1 is None:
                print(
                    f"WARNING: Resource file '{resource_original_filepath.name}' not found",
                    file=sys.stderr
                )
                continue

            filename_to_data[resource_original_filepath.name] = \
                (sha1, s3_md5, mime_type, resource_original_filepath)
            node.attrib["src"] = f"../{RESOURCES_DIR_NAME}/{sha1}"

        for node in doc.xpath(
                '//x:iframe',
                namespaces={"x": "http://cnx.rice.edu/cnxml"}
        ):
            resource_original_src = node.attrib["src"]

            abs_path_pattern = re.compile("^https?://")
            if abs_path_pattern.match(resource_original_src):
                continue  # pragma: no cover

            resource_original_filepath = \
                (cnxml_file.parent / resource_original_src).resolve()

            foopath = (cnxml_file.parent / "../../media").resolve()
            new_resource_child_path = resource_original_filepath.relative_to(foopath)

            new_resource_src = f"../{RESOURCES_DIR_NAME}/{new_resource_child_path}"

            print(f"rewriting iframe source from {resource_original_src} to {new_resource_src}")
            node.attrib["src"] = new_resource_src

        with cnxml_file.open(mode="wb") as f:
            doc.write(f, encoding="utf-8", xml_declaration=False)

    for resource_original_name in filename_to_data:
        sha1, s3_md5, mime_type, resource_original_filepath = \
            filename_to_data[resource_original_name]

        checksum_resource_file = resources_dir / sha1

        shutil.move(str(resource_original_filepath), str(checksum_resource_file))
        create_json_metadata(resources_dir, sha1, mime_type, s3_md5, resource_original_name)

    # NOTE: As part of CNX-1274 (https://github.com/openstax/cnx/issues/1274),
    # we're adding support for relative image URLs which may mean over time
    # media files can come from more than one directory. If so, the assumption
    # here that all media files come from an original_resources_dir input
    # should be revisited.
    for unused_resource_file in original_resources_dir.glob('**/*'):
        shutil.move(str(unused_resource_file), unused_resources_dump)
        print(
            f"WARNING: Resource file '{unused_resource_file.name}' seems to be unused",
            file=sys.stderr
        )


if __name__ == "__main__":  # pragma: no cover
    main()
