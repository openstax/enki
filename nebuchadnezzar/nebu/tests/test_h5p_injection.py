from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
from nebu import h5p_injection


@pytest.fixture
def h5p_interactive_base():
    return {"content": {}, "metadata": {}, "h5p": {"mainLibrary": "Test"}}


@contextmanager
def set_library_action(library, action):
    clone = deepcopy(h5p_injection.SUPPORTED_LIBRARIES)
    h5p_injection.SUPPORTED_LIBRARIES[
        library
    ] = h5p_injection.SupportedLibrary(lambda _: [], action)
    yield
    h5p_injection.SUPPORTED_LIBRARIES = clone


def test_questions_from_h5p_errors(h5p_interactive_base):
    nickname = "test"

    # GIVEN: Content that causes KeyError
    test_content = dict(h5p_interactive_base)
    missing_key = "boop"

    def raise_key_error(*_args, **_kwargs):
        raise KeyError(missing_key)

    lib = test_content["h5p"]["mainLibrary"]
    with set_library_action(lib, raise_key_error):
        # WHEN: Questions are constructed
        with pytest.raises(h5p_injection.H5PContentError) as hie:
            h5p_injection.questions_from_h5p(nickname, test_content)
        # THEN: The error explains the problem
        assert hie.match(nickname)
        assert hie.match(h5p_injection.POSSIBLE_PROBLEMS)
        assert hie.match(
            h5p_injection.MISSING_PROPERTY_ERROR.format(key=missing_key)
        )

    # GIVEN: Content that causes an assertion error
    test_content = dict(h5p_interactive_base)
    assertion_message = "boop"

    def bad_assertion(*_args, **_kwargs):
        assert False, assertion_message

    lib = test_content["h5p"]["mainLibrary"]
    with set_library_action(lib, bad_assertion):
        # WHEN: Questions are constructed
        with pytest.raises(h5p_injection.H5PContentError) as hie:
            h5p_injection.questions_from_h5p(nickname, test_content)
        # THEN: The error explains the problem
        assert hie.match(nickname)
        assert hie.match(h5p_injection.POSSIBLE_PROBLEMS)
        assert hie.match(assertion_message)


def test_unsupported_library_error(h5p_interactive_base, monkeypatch):
    monkeypatch.setattr(h5p_injection, "SUPPORTED_LIBRARIES", {})
    test_content = dict(h5p_interactive_base)
    test_library = "unsupported-library-for-testing"
    test_content["h5p"]["mainLibrary"] = test_library
    with pytest.raises(h5p_injection.UnsupportedLibraryError) as ule:
        h5p_injection.questions_from_h5p("unsupported", h5p_interactive_base)
    assert ule.value.args[0] == test_library


def test_load_h5p_interactive(git_collection_container, git_path_resolver):
    public_interactives = [
        p.parent
        for p in Path(git_collection_container.public_root).glob("**/h5p.json")
    ]
    merged = public_only = None
    for public_interactive in public_interactives:
        nickname = public_interactive.name
        public_path = git_path_resolver.get_public_interactives_path(nickname)
        private_path = git_path_resolver.get_private_interactives_path(
            nickname
        )
        if Path(private_path).exists():
            merged = h5p_injection.load_h5p_interactive(
                public_path, private_path
            )
            public_only = h5p_injection.load_h5p_interactive(public_path)
            break
    else:
        pytest.fail("Could not find private interactive")
    assert merged != public_only
    assert merged != {}
