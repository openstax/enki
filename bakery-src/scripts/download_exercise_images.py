"""
Download images from exercises at the end of assemble step.
Save images into resources folder as checksum filename.
Replace exercise http links to local resources links.
"""

import sys
import requests
import shutil
from pathlib import Path
from lxml import etree
from tempfile import SpooledTemporaryFile
from . import utils

EXERCISE_IMAGE_URL_PREFIX = 'http'


def fetch_and_replace_external_exercise_images(resources_dir, input_xml, output_xml):
    doc = etree.parse(str(input_xml))
    for node in doc.xpath(
            '//x:img[starts-with(@src, "{}")]'.format(EXERCISE_IMAGE_URL_PREFIX),
            namespaces={"x": "http://www.w3.org/1999/xhtml"}
    ):
        image_url = node.get('src')
        print('Downloading: ' + image_url)
        with SpooledTemporaryFile() as tmp_file:
            # It's possible to optimise it more in future with async parallel downloads?
            # async download example https://stackoverflow.com/a/73194807/756056
            # or https://www.python-httpx.org/
            with requests.get(image_url, stream=True) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    tmp_file.write(chunk)
            sha1, s3_md5 = utils.get_checksums(str(tmp_file))
            local_resource = Path(resources_dir) / Path(sha1)
            with open(local_resource, 'wb') as local_resource_file:
                shutil.copyfileobj(tmp_file, local_resource_file)

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
