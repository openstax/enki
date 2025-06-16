"""
Download images from exercises at the end of assemble step.
Save images into resources folder as checksum filename.
Replace exercise http links to local resources links.
"""

import sys
import requests
import shutil
import hashlib
from pathlib import Path
from tempfile import SpooledTemporaryFile

from lxml import etree

from .utils import get_checksums, get_size, create_json_metadata, get_mime_type
from .profiler import timed
from . import excepthook


excepthook.attach(sys)

EXERCISE_IMAGE_URL_PREFIX = 'http'


@timed
def fetch_and_replace_external_exercise_images(resources_dir, input_xml, output_xml):
    doc = etree.parse(str(input_xml))
    with requests.Session() as session:
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
                with session.get(image_url, stream=True) as response:
                    response.raise_for_status()
                    # 1MB chunks
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        tmp_file.write(chunk)
                tmp_file.seek(0)  # important to read whole file for sha1
                sha1 = hashlib.sha1(tmp_file.read()).hexdigest()
                tmp_file.seek(0)  # important for copyfileobj to run completely
                local_resource = Path(resources_dir) / Path(sha1)
                with open(local_resource, 'wb') as local_resource_file:
                    shutil.copyfileobj(tmp_file, local_resource_file)

            sha1_local, s3_md5 = get_checksums(str(local_resource))
            if sha1 != sha1_local:  # pragma: no cover
                raise ValueError(
                    f'SHA1 internal values do not match! That should never happen! {sha1} != {sha1_local}')
            mime_type = get_mime_type(str(local_resource))
            width, height = get_size(str(local_resource))
            create_json_metadata(
                resources_dir, sha1, mime_type, s3_md5, image_url, width, height)

            new_local_src = '../resources/' + sha1
            print('to local: ' + new_local_src)
            node.set('src', new_local_src)
        doc.write(output_xml, encoding="utf8")


@timed
def main():  # pragma: no cover
    resources_dir = Path(sys.argv[1]).resolve(strict=True)
    input_xml = Path(sys.argv[2]).resolve(strict=True)
    output_xml = sys.argv[3]
    fetch_and_replace_external_exercise_images(
        resources_dir, input_xml, output_xml)


if __name__ == "__main__":  # pragma: no cover
    main()
