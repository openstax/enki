"""
Download images from exercises at the end of assemble step.
Save images into resources folder as checksum filename.
Replace exercise http links to local resources links.
"""

import sys
import requests
import uuid
import shutil
from pathlib import Path
from lxml import etree
from tempfile import TemporaryDirectory
from . import utils

EXERCISE_IMAGE_URL_PREFIX = 'http'


def _download_file(url, output_filename):
    """Download URL content into a file as stream (large file support, low memory)"""
    # It's possible to optimise it more in future with async parallel downloads?
    # async download example https://stackoverflow.com/a/73194807/756056
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(output_filename, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                out_file.write(chunk)
        return output_filename


def _download_as_uuid(download_dir, image_url):
    unique_filename = str(uuid.uuid4())
    output_filename = Path(download_dir) / Path(unique_filename)
    _download_file(image_url, str(output_filename))
    return output_filename


def fetch_and_replace_external_exercise_images(resources_dir, input_xml, output_xml):
    doc = etree.parse(str(input_xml))
    with TemporaryDirectory() as temp_dir:
        for node in doc.xpath(
                '//x:img[starts-with(@src, "{}")]'.format(EXERCISE_IMAGE_URL_PREFIX),
                namespaces={"x": "http://www.w3.org/1999/xhtml"}
        ):
            image_url = node.get('src')
            print('Downloading: ' + image_url)
            temp_resource = _download_as_uuid(temp_dir, image_url)
            sha1, s3_md5 = utils.get_checksums(str(temp_resource))
            local_resource = Path(resources_dir) / Path(sha1)
            shutil.move(str(temp_resource), str(local_resource))

            mime_type = utils.get_mime_type(str(local_resource))
            width, height = utils.get_size(str(local_resource))
            utils.create_json_metadata(
                resources_dir, sha1, mime_type, s3_md5, image_url, width, height)

            new_local_src = '../resources/' + sha1
            print('to local: ' + new_local_src)
            node.set('src', new_local_src)
    doc.write(output_xml, encoding="utf8")


def main():  # pragma: no cover
    resources_dir = Path(sys.argv[1]).resolve(strict=True)
    input_xml = Path(sys.argv[2]).resolve(strict=True)
    output_xml = sys.argv[3]
    fetch_and_replace_external_exercise_images(resources_dir, input_xml, output_xml)


if __name__ == "__main__":  # pragma: no cover
    main()
