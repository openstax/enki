"""Optimize images referenced by an ancillary index.html file."""

import argparse
import json
import os
import sys
from pathlib import Path

from lxml import etree
from PIL import Image, features

from . import excepthook
from .utils import get_checksums, get_size


excepthook.attach(sys)

DEFAULT_MAX_SIZE = 1_000_000
DEFAULT_SOURCE_TYPES = ('image/png', 'image/jpeg')
DEFAULT_FORMAT = 'webp'
DEFAULT_QUALITY = 90
DEFAULT_METHOD = 6

TARGET_FORMATS = {
    'webp': {
        'pillow_format': 'WEBP',
        'mime_type': 'image/webp',
    },
}


class ImageOptimizationError(Exception):
    """Raised when an image cannot be optimized within the configured limit."""


def _resource_name_from_src(src):
    prefixes = ('./resources/', 'resources/')
    for prefix in prefixes:
        if src.startswith(prefix):
            resource_name = src[len(prefix):]
            if resource_name and '/' not in resource_name:
                return resource_name
            return None
    return None


def _load_metadata(metadata_path):
    try:
        with metadata_path.open() as metadata_file:
            return json.load(metadata_file)
    except FileNotFoundError as error:
        raise ImageOptimizationError(
            f'No metadata file found for resource {metadata_path.stem}: '
            f'{metadata_path}'
        ) from error


def _write_metadata(metadata_path, metadata):
    with metadata_path.open('w') as metadata_file:
        json.dump(metadata, metadata_file)


def _candidate_for_image(
    source_path,
    metadata_path,
    target_format,
):
    metadata = _load_metadata(metadata_path)
    target = TARGET_FORMATS[target_format]
    temporary_path = source_path.with_name(
        f'.{source_path.name}.optimized.{target_format}'
    )

    try:

        with Image.open(source_path) as image:
            try:
                image.save(
                    temporary_path,
                    format=target['pillow_format'],
                    quality=DEFAULT_QUALITY,
                    method=DEFAULT_METHOD,
                )
            except Exception as error:
                raise ImageOptimizationError(
                    f'Could not convert image to {target_format}: '
                    f'{source_path}: {error}'
                ) from error

        optimized_size = temporary_path.stat().st_size
        source_size = source_path.stat().st_size
        new_sha1, new_s3_md5 = get_checksums(str(temporary_path))
        if new_sha1 is None or new_s3_md5 is None:  # pragma: no cover
            raise ImageOptimizationError(
                f'Could not calculate checksums for {temporary_path}'
            )
        if new_sha1 == source_path.name:
            raise ImageOptimizationError(
                f'Optimized resource has the same SHA-1 as the source: '
                f'{source_path}'
            )

        width = metadata.get('width')
        height = metadata.get('height')
        if width is None or height is None:
            width, height = get_size(str(source_path))

        new_metadata = {
            'original_name': metadata.get('original_name', source_path.name),
            'mime_type': target['mime_type'],
            's3_md5': new_s3_md5,
            'sha1': new_sha1,
            'width': width,
            'height': height,
        }

        return {
            'source_path': source_path,
            'metadata_path': metadata_path,
            'source_size': source_size,
            'optimized_size': optimized_size,
            'new_sha1': new_sha1,
            'new_metadata': new_metadata,
            'temporary_path': temporary_path,
        }
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _update_index(index_path, replacements):
    tree = etree.parse(str(index_path))
    changed = False
    for image in tree.xpath('//*[local-name()="img"][@src]'):
        src = image.get('src')
        resource_name = _resource_name_from_src(src)
        replacement = replacements.get(resource_name)
        if replacement is None:
            continue

        image.set('src', src.replace(resource_name, replacement['new_sha1'], 1))
        image.set('data-media-type', replacement['mime_type'])
        changed = True

    if changed:
        temporary_index_path = index_path.with_name(
            f'.{index_path.name}.optimized'
        )
        tree.write(
            str(temporary_index_path),
            encoding='utf8',
            xml_declaration=False,
        )
        return temporary_index_path
    return None


def optimize_images(
    index_path,
    max_size=DEFAULT_MAX_SIZE,
    source_types=DEFAULT_SOURCE_TYPES,
    target_format=DEFAULT_FORMAT,
    on_exceed='error',
    keep_original=False,
):
    """Optimize oversized images referenced by ``index_path``.

    The returned value is the number of images replaced. Files are only
    changed after every candidate has been converted and validated.
    """
    index_path = Path(index_path).resolve(strict=True)
    resources_dir = index_path.parent / 'resources'
    if not resources_dir.is_dir():
        raise ImageOptimizationError(f'Resources directory not found: {resources_dir}')
    if max_size <= 0:
        raise ValueError('max_size must be greater than zero')
    if target_format not in TARGET_FORMATS:
        raise ValueError(f'Unsupported target format: {target_format}')
    if on_exceed not in ('error', 'warn'):
        raise ValueError(f'Unsupported on_exceed value: {on_exceed}')
    if not features.check('webp'):
        raise ImageOptimizationError('Pillow was built without WebP support')

    tree = etree.parse(str(index_path))
    referenced_images = {}
    for image in tree.xpath('//*[local-name()="img"][@src]'):
        src = image.get('src')
        resource_name = _resource_name_from_src(src)
        if resource_name is not None:
            referenced_images[resource_name] = image

    candidates = []
    try:
        for resource_name in referenced_images:
            resource_path = resources_dir / resource_name
            if not resource_path.is_file():
                raise ImageOptimizationError(
                    f'Referenced image does not exist: {resource_path}'
                )

            metadata_path = resource_path.with_name(f'{resource_name}.json')
            metadata = _load_metadata(metadata_path)
            if metadata.get('mime_type') not in source_types:
                continue
            if resource_path.stat().st_size <= max_size:
                continue

            candidates.append(
                _candidate_for_image(
                    resource_path,
                    metadata_path,
                    target_format,
                )
            )
    except Exception:
        for candidate in candidates:
            candidate['temporary_path'].unlink(missing_ok=True)
        raise

    replacements = {}
    for candidate in candidates:
        source_size = candidate['source_size']
        optimized_size = candidate['optimized_size']
        if optimized_size > max_size:
            message = (
                f'Optimized image is too large: {candidate["source_path"]} '
                f'({optimized_size} bytes; maximum {max_size})'
            )
            if on_exceed == 'error':
                for pending in candidates:
                    pending['temporary_path'].unlink(missing_ok=True)
                raise ImageOptimizationError(message)
            print(f'WARNING: {message}', file=sys.stderr)

        if optimized_size >= source_size:
            print(
                f'WARNING: Optimized image is not smaller: '
                f'{candidate["source_path"]}',
                file=sys.stderr,
            )
            candidate['temporary_path'].unlink(missing_ok=True)
            continue

        replacements[candidate['source_path'].name] = {
            'new_sha1': candidate['new_sha1'],
            'mime_type': TARGET_FORMATS[target_format]['mime_type'],
            'candidate': candidate,
        }

    if not replacements:
        return 0

    try:
        temporary_index_path = _update_index(index_path, replacements)
    except Exception:
        for candidate in candidates:
            candidate['temporary_path'].unlink(missing_ok=True)
        raise
    try:
        for _, replacement in replacements.items():
            candidate = replacement['candidate']
            new_path = resources_dir / replacement['new_sha1']
            new_metadata_path = new_path.with_name(f'{new_path.name}.json')
            os.replace(candidate['temporary_path'], new_path)
            _write_metadata(new_metadata_path, candidate['new_metadata'])

        if temporary_index_path is not None:
            os.replace(temporary_index_path, index_path)

        if not keep_original:
            for _, replacement in replacements.items():
                candidate = replacement['candidate']
                candidate['source_path'].unlink()
                candidate['metadata_path'].unlink()

    except Exception:
        if temporary_index_path is not None:
            temporary_index_path.unlink(missing_ok=True)
        raise
    finally:
        for candidate in candidates:
            candidate['temporary_path'].unlink(missing_ok=True)

    for _, replacement in replacements.items():
        candidate = replacement['candidate']
        print(
            f'Optimized {candidate["source_path"]}: '
            f'{candidate["source_size"]} -> {candidate["optimized_size"]} bytes'
        )
    return len(replacements)


def main():  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument('index_html', type=Path)
    parser.add_argument('--type', dest='source_types', action='append')
    parser.add_argument('--max-size', type=int, default=DEFAULT_MAX_SIZE)
    parser.add_argument('--format', dest='target_format', default=DEFAULT_FORMAT,
                        choices=sorted(TARGET_FORMATS))
    parser.add_argument('--on-exceed', choices=('error', 'warn'), default='error')
    parser.add_argument('--keep-original', action='store_true')
    args = parser.parse_args()

    optimize_images(
        args.index_html,
        max_size=args.max_size,
        source_types=tuple(args.source_types or DEFAULT_SOURCE_TYPES),
        target_format=args.target_format,
        on_exceed=args.on_exceed,
        keep_original=args.keep_original,
    )


if __name__ == '__main__':  # pragma: no cover
    main()
