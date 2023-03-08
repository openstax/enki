"""Map resource files used in CNXML to provided path"""
import re
import shutil
import sys
import os
from pathlib import Path

from lxml import etree

from .utils import get_checksums, get_mime_type, get_size, create_json_metadata
from .profiler import timed

# relative links must work both locally, on PDF, and on REX, and images are
# uploaded with the prefix 'resources/' in S3 for REX
# so the output directory name MUST be resources
RESOURCES_DIR_NAME = 'resources'


@timed
def all_data_to_json(resources_dir, filename_to_data):
    """ Convert python dictionary of metadata into json files """
    for resource_original_name in filename_to_data:
        sha1, s3_md5, mime_type, resource_original_filepath, width, height = \
            filename_to_data[resource_original_name]

        checksum_resource_file = resources_dir / sha1

        shutil.move(str(resource_original_filepath),
                    str(checksum_resource_file))
        create_json_metadata(
            resources_dir, sha1, mime_type, s3_md5, resource_original_name, width, height)


@timed
def rename(filename_to_data, resource_original_filepath, is_image):
    sha1, s3_md5 = get_checksums(
        str(resource_original_filepath)
    )
    mime_type = get_mime_type(str(resource_original_filepath))

    if sha1 is None:
        return None

    opt_width = None
    opt_height = None
    if is_image:
        opt_width, opt_height = get_size(str(resource_original_filepath))
    filename_to_data[resource_original_filepath.name] = \
        (sha1, s3_md5, mime_type, resource_original_filepath, opt_width, opt_height)
    return f"../{RESOURCES_DIR_NAME}/{sha1}"


@timed
def rename_file_to_resource(filename_to_data, doc, cnxml_file, xpath, attribute_name, context_dir, is_image):
    for node in doc.xpath(
            xpath,
            namespaces={"c": "http://cnx.rice.edu/cnxml"}
    ):
        resource_original_src = node.attrib[attribute_name]
        resource_original_filepath = (
            context_dir / resource_original_src).resolve()
        new_path = rename(filename_to_data,
                          resource_original_filepath, is_image)
        if new_path is None:
            print(
                f"WARNING: Resource file '{resource_original_filepath}' not found",
                file=sys.stderr
            )
            if os.environ.get('HACK_CNX_LOOSENESS', False) is not False:  # pragma: no cover
                # Replace node with a comment
                text = f'[missing_resource: {resource_original_src}]'
                comment = etree.Comment(etree.tostring(node))
                comment.tail = text
                parent = node.getparent()
                parent.replace(node, comment)
                continue
            else:
                print(f"WARNING: Resource file '{resource_original_filepath}' not found",
                      file=sys.stderr)
        else:
            node.attrib[attribute_name] = new_path


@timed
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

        rename_file_to_resource(filename_to_data, doc, cnxml_file,
                                '//c:image', 'src', cnxml_file.parent, True)
        # EPUB: CNX books sometimes link to files like MP3 in the Basic Elements of Music
        rename_file_to_resource(filename_to_data, doc, cnxml_file,
                                '//c:link[@resource]', 'resource', original_resources_dir, False)
        # EPUB: CNX books sometimes use an <object> tag to embed an interactive (Like Mathematica)
        rename_file_to_resource(filename_to_data, doc, cnxml_file,
                                '//c:object[@src][not(starts-with(@src, "http"))]', 'src',
                                original_resources_dir, False)
        # EPUB: Some books have Adobe Flash content which is no longer used on the web
        rename_file_to_resource(filename_to_data, doc, cnxml_file,
                                '//c:flash[@src][not(starts-with(@src, "."))]', 'src', original_resources_dir,
                                False)

        for node in doc.xpath(
                '//c:iframe',
                namespaces={"c": "http://cnx.rice.edu/cnxml"}
        ):
            resource_original_src = node.attrib["src"]

            abs_path_pattern = re.compile("^https?://")
            if abs_path_pattern.match(resource_original_src):
                continue  # pragma: no cover

            resource_original_filepath = \
                (cnxml_file.parent / resource_original_src).resolve()

            foopath = (cnxml_file.parent / "../../media").resolve()
            new_resource_child_path = resource_original_filepath.relative_to(
                foopath)

            new_resource_src = f"../{RESOURCES_DIR_NAME}/{new_resource_child_path}"

            print(
                f"rewriting iframe source from {resource_original_src} to {new_resource_src}")
            node.attrib["src"] = new_resource_src

        with cnxml_file.open(mode="wb") as f:
            doc.write(f, encoding="utf-8", xml_declaration=False)

    all_data_to_json(resources_dir, filename_to_data)

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
