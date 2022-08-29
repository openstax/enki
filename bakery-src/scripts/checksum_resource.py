import json
import os
import sys
from pathlib import Path

from lxml import etree

from . import utils

RESOURCES_DIR = 'resources'


def create_symlink(img_filename, output_dir, sha1):
    """ Create symlinks for resources to raw files """
    raw_img_filename = os.path.realpath(img_filename)
    dest_path = os.path.join(output_dir, RESOURCES_DIR)
    dest_img_filename = os.path.join(dest_path, sha1)
    rel_raw_img_filename = os.path.relpath(raw_img_filename, dest_path)
    try:
        # set a relative symlink to raw file
        os.symlink(rel_raw_img_filename, dest_img_filename)
    except FileExistsError:  # pragma: no cover
        # ignore symlink file existing
        pass


def create_json_metadata(output_dir, sha1, mime_type, s3_md5, original_name, width, height):
    """ Create json with MIME type of a (symlinked) resource file """
    data = {}
    data['original_name'] = original_name
    data['mime_type'] = mime_type
    data['s3_md5'] = s3_md5
    data['sha1'] = sha1
    data['width'] = width
    data['height'] = height
    json_filename = os.path.join(output_dir, RESOURCES_DIR, sha1 + '.json')
    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)


def generate_checksum_resources_from_xhtml(filename, output_dir):
    """ Go through HTML and checksum/copy/mime type all <img> and <a>
    resources
    """
    doc = etree.parse(filename)
    source_path = os.path.dirname(filename)
    basename = os.path.basename(filename)
    module_name = os.path.splitext(basename)[0]
    # get all img @src resources
    img_xpath = '//x:img[@src and not(starts-with(@src, "http") or ' \
                'starts-with(@src, "//"))]'
    for node in doc.xpath(img_xpath,
                          namespaces={'x': 'http://www.w3.org/1999/xhtml'}):
        img_filename = node.attrib['src']
        img_filename = os.path.join(source_path, img_filename)
        img_basename = os.path.basename(img_filename)

        sha1, s3_md5 = utils.get_checksums(img_filename)
        mime_type = utils.get_mime_type(img_filename)
        width, height = utils.get_size(img_filename)

        if sha1:  # file exists
            node.attrib['src'] = '../' + RESOURCES_DIR + '/' + sha1

            create_symlink(img_filename, output_dir, sha1)
            create_json_metadata(output_dir, sha1, mime_type, s3_md5,
                                 img_basename, width, height)

    # get all a @href resources
    href_xpath = '//x:a[@href and not(starts-with(@href, "http") or ' \
                 'starts-with(@href, "//") or starts-with(@href, "#"))]'
    for node in doc.xpath(href_xpath,
                          namespaces={'x': 'http://www.w3.org/1999/xhtml'}):
        img_filename = node.attrib['href']

        # fix a @href links to module_name directories
        # they are pointing relatively to ./image.jpg but need to point
        # to ./m123/image.jpg
        img_filename = os.path.join(source_path, module_name, img_filename)
        img_basename = os.path.basename(img_filename)

        sha1, s3_md5 = utils.get_checksums(img_filename)
        mime_type = utils.get_mime_type(img_filename)
        width, height = utils.get_size(img_filename)

        if sha1:  # file exists
            node.attrib['href'] = '../' + RESOURCES_DIR + '/' + sha1

            create_symlink(img_filename, output_dir, sha1)
            create_json_metadata(output_dir, sha1, mime_type, s3_md5,
                                 img_basename, width, height)

    output_file = os.path.join(output_dir, basename)
    # note: non self closing tags in xhtml are probably not respected here
    with open(output_file, 'wb') as f:
        doc.write(f, encoding="ASCII", xml_declaration=False)


def mkdir_resources(path):
    resources = os.path.join(path, RESOURCES_DIR)
    os.makedirs(resources, exist_ok=True)


def main():
    """Main function"""
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    out_dir = Path(sys.argv[2])
    mkdir_resources(out_dir)
    for xhtml_file in Path(in_dir).glob('*.xhtml'):
        generate_checksum_resources_from_xhtml(str(xhtml_file), out_dir)


if __name__ == "__main__":  # pragma: no cover
    main()
