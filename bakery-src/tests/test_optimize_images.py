import hashlib
import json

import pytest
from lxml import etree
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from bakery_scripts.optimize_images import (
    ImageOptimizationError,
    optimize_images,
)


XHTML_NS = {'x': 'http://www.w3.org/1999/xhtml'}


def make_ancillary(tmp_path):
    ancillary_dir = tmp_path / 'ancillary'
    resources_dir = ancillary_dir / 'resources'
    resources_dir.mkdir(parents=True)

    old_sha1 = 'a' * 40
    image_path = resources_dir / old_sha1
    image = Image.new('RGB', (100, 100), (255, 0, 0))
    png_info = PngInfo()
    png_info.add_text('padding', 'x' * 5000)
    image.save(image_path, format='PNG', pnginfo=png_info)

    metadata = {
        'original_name': 'image.png',
        'mime_type': 'image/png',
        's3_md5': '"old-md5"',
        'sha1': old_sha1,
        'width': 100,
        'height': 100,
    }
    (resources_dir / f'{old_sha1}.json').write_text(json.dumps(metadata))

    index_path = ancillary_dir / 'index.html'
    index_path.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        f'<img src="./resources/{old_sha1}" data-media-type="image/png"/>'
        '</body></html>'
    )
    return ancillary_dir, index_path, image_path


def image_reference(index_path):
    tree = etree.parse(str(index_path))
    return tree.xpath('//x:img', namespaces=XHTML_NS)[0]


def test_optimize_images_replaces_oversized_png_and_updates_metadata(tmp_path):
    _, index_path, old_image_path = make_ancillary(tmp_path)

    replaced = optimize_images(index_path, max_size=1000)

    assert replaced == 1
    image = image_reference(index_path)
    new_sha1 = image.get('src').split('/')[-1]
    new_image_path = index_path.parent / 'resources' / new_sha1
    new_metadata_path = new_image_path.with_name(f'{new_sha1}.json')

    assert new_sha1 != old_image_path.name
    assert new_image_path.is_file()
    assert new_image_path.stat().st_size <= 1000
    assert not old_image_path.exists()
    assert not old_image_path.with_name(f'{old_image_path.name}.json').exists()
    assert image.get('data-media-type') == 'image/webp'

    metadata = json.loads(new_metadata_path.read_text())
    assert metadata['mime_type'] == 'image/webp'
    assert metadata['sha1'] == new_sha1
    assert metadata['width'] == 100
    assert metadata['height'] == 100
    assert metadata['s3_md5'].startswith('"')
    assert hashlib.sha1(new_image_path.read_bytes()).hexdigest() == new_sha1


def test_optimize_images_errors_without_modifying_files_when_limit_remains_exceeded(
    tmp_path,
):
    _, index_path, old_image_path = make_ancillary(tmp_path)
    original_index = index_path.read_text()

    with pytest.raises(ImageOptimizationError, match='too large'):
        optimize_images(index_path, max_size=10)

    assert old_image_path.exists()
    assert index_path.read_text() == original_index
    assert list(old_image_path.parent.glob('.*.optimized.*')) == []


def test_optimize_images_warns_and_keeps_smaller_result_when_limit_is_exceeded(
    tmp_path, capsys
):
    _, index_path, old_image_path = make_ancillary(tmp_path)

    optimize_images(index_path, max_size=10, on_exceed='warn')

    assert 'Optimized image is too large' in capsys.readouterr().err
    assert not old_image_path.exists()
    assert image_reference(index_path).get('data-media-type') == 'image/webp'


def test_optimize_images_can_keep_original(tmp_path):
    _, index_path, old_image_path = make_ancillary(tmp_path)

    optimize_images(index_path, max_size=1000, keep_original=True)

    assert old_image_path.exists()
    assert image_reference(index_path).get('src').split('/')[-1] != old_image_path.name


def test_optimize_images_ignores_images_at_or_below_limit(tmp_path):
    _, index_path, old_image_path = make_ancillary(tmp_path)
    max_size = old_image_path.stat().st_size

    assert optimize_images(index_path, max_size=max_size) == 0
    assert old_image_path.exists()
    assert image_reference(index_path).get('src').split('/')[-1] == old_image_path.name
