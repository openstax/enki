import os
import hashlib
import logging
import mimetypes

import filetype
import imagesize


logger = logging.getLogger("nebuchadnezzar")


# same as boto3 default chunk size. Don't modify.
BUF_SIZE = 8 * 1024 * 1024


def get_checksums(filename):
    """ generate SHA1 and S3 MD5 etag checksums from file """
    sha1 = hashlib.sha1()
    md5s = []
    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
            md5s.append(hashlib.md5(data))
    # chunked calculation for AWS S3 MD5 etag
    # https://stackoverflow.com/a/43819225/756056
    #
    # AWS needs the MD5 quoted inside the string json value.
    # Despite looking like a mistake, this is correct behavior.
    if len(md5s) < 1:
        s3_md5 = '"{}"'.format(
            hashlib.md5().hexdigest())  # pragma: no cover
    elif len(md5s) == 1:
        s3_md5 = '"{}"'.format(md5s[0].hexdigest())
    else:  # pragma: no cover
        digests = b''.join(m.digest() for m in md5s)
        digests_md5 = hashlib.md5(digests)
        s3_md5 = '"{}-{}"'.format(digests_md5.hexdigest(), len(md5s))
    return sha1.hexdigest(), s3_md5


def json_metadata_factory(
    sha1, mime_type, s3_md5, original_name, width, height
):
    """Create json with MIME type and other metadata of resource file"""
    data = {}
    data["original_name"] = original_name
    data["mime_type"] = mime_type
    data["s3_md5"] = s3_md5
    data["sha1"] = sha1
    data["width"] = width
    data["height"] = height
    return data


def get_mime_type(filepath):
    mime_type = None
    try:
        guessed = filetype.guess(filepath)
        if guessed is not None:
            mime_type = guessed.mime
    except IOError:
        pass
    if mime_type is None:
        logger.warning(
            f"Could not guess mime type from file contents: {filepath}"
        )
        mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type if mime_type is not None else ''


# Returns (-1, -1) if not an image
def get_size(filepath):
    """ get width and height of file with imagesize """
    width = height = -1
    try:
        width, height = imagesize.get(filepath)
    finally:
        return int(width), int(height)


def get_media_metadata(resource_abs_path, is_image):
    resource_name = os.path.basename(resource_abs_path)
    sha1, s3_md5 = get_checksums(resource_abs_path)
    mime_type = get_mime_type(resource_abs_path)
    opt_width, opt_height = (
        get_size(resource_abs_path) if is_image else (None, None)
    )
    metadata = json_metadata_factory(
        sha1,
        mime_type,
        s3_md5,
        resource_name,
        opt_width,
        opt_height,
    )
    return sha1, metadata
