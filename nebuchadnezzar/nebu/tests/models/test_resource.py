import hashlib

from cnxepub.models import RESOURCE_HASH_TYPE

from nebu.models.resource import FileSystemResource


def test(collection_data):
    filename = 'CNX_Stats_C01_M10_003.jpg'
    filepath = collection_data / 'm46882' / filename

    # Create the resource object (target)
    res = FileSystemResource(filepath)

    # Test the interface behaves the same as a cnx-epub Resource
    assert res.id == filename
    assert res.media_type is None  # b/c we didn't set it.
    assert res.filename == filename

    with filepath.open('rb') as fb:
        content = fb.read()

    with res.open() as open_file:
        assert content == open_file.read()

    digest = hashlib.new(RESOURCE_HASH_TYPE, content).hexdigest()
    assert res.hash == digest
    # And reassign to ensure it doesn't lookup the value again
    res._hash = 'foobar'
    assert res.hash == 'foobar'
