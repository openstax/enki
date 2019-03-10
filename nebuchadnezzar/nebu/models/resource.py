import hashlib
from contextlib import contextmanager

from cnxepub.models import RESOURCE_HASH_TYPE


class FileSystemResource(object):
    """A binary object used within the context of a ``Document``.
    It is typically referenced within the document's content.

    :param filepath: file path to the resource
    :type filepath: :class:`pathlib.Path`
    :param media_type: media-type of the file
    :type media_type: str

    """
    # implements(IResource)

    def __init__(self, filepath, media_type=None):
        self._filepath = filepath
        self.media_type = media_type
        self._hash = None

    @property
    def id(self):
        return self._filepath.name

    @property
    def filename(self):
        return self._filepath.name

    @property
    def hash(self):
        if not self._hash:
            with self._filepath.open('rb') as fb:
                self._hash = hashlib.new(
                    RESOURCE_HASH_TYPE,
                    fb.read()
                ).hexdigest()
        return self._hash

    @contextmanager
    def open(self):
        with self._filepath.open('rb') as fb:
            yield fb
