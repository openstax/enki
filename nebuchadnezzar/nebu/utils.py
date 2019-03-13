import os.path
from pathlib import Path


def relative_path(path, start=Path('.')):
    """This is a :class:`pathlib.Path` compatible way of building relative
    paths. ``Path.relative_to()`` does exist, but does not correctly apply
    sibling descendent relationships (aka ``../``). ``os.path.relpath`` does
    what is wanted, so we use it, but with ``pathlib`` objects.

    Note, this function requires ``path`` and ``start`` to be resolvable.
    Or in other words, they must exist, so that we can obtain an absolute
    path. Directly use ``os.path.relpath`` if this is a problem.

    :param path: the path to make relative
    :type path: :class:`pathlib.Path`
    :param start: starting location to make the given ``path`` relative to
    :type start: :class:`pathlib.Path`
    :return: relative path
    :rtype: :class:`pathlib.Path`

    """
    p = str(path.resolve())
    s = str(start.resolve())
    return Path(os.path.relpath(p, start=s))
