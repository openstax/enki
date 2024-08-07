import json

from nebu.utils import recursive_merge, try_parse_bool
import pytest


def test_recursive_merge_dict():
    a = {"x": None, "y": [None], "z": {"w": [None]}}
    b = {"x": 2, "y": [3], "z": {"w": [2]}}
    orig_a, orig_b = json.dumps(a), json.dumps(b)
    merged = recursive_merge(a, b)
    post_merge_a, post_merge_b = json.dumps(a), json.dumps(b)
    # Should not mutate originals
    assert orig_a == post_merge_a
    assert orig_b == post_merge_b
    # Default: keep rhs
    assert merged["x"] == 2
    # Default: concat array
    assert merged["y"] == [3]
    # Default: recursively merge dicts
    assert merged["z"]["w"] == [2]
    # Override default behavior to add int and/or float
    custom_default = recursive_merge(
        {"x": 1, "y": [2], "z": {"w": [1]}},
        {"x": 2, "y": [3], "z": {"w": [2]}},
        default=lambda a, b: a + b if isinstance(a, (int, float)) else b
    )
    assert custom_default["x"] == 3
    default_favors_not_none = recursive_merge([1], [None])
    assert default_favors_not_none == [1]
    default_favors_not_none = recursive_merge([1], [None])
    assert default_favors_not_none == [1]
    default_favors_not_none = recursive_merge({"a": [1]}, {"a": [None]})
    assert default_favors_not_none["a"] == [1]
    default_favors_not_none = recursive_merge({"a": [1]}, {"b": [None]})
    assert default_favors_not_none["a"] == [1]
    assert default_favors_not_none["b"] == [None]
    default_favors_not_none = recursive_merge([1, None, 3], [None, 2, None])
    assert default_favors_not_none == [1, 2, 3]
    with pytest.raises(Exception) as e:
        recursive_merge([1], ["s"])
    assert e.match("Cannot merge")


@pytest.mark.parametrize(
    "value,result",
    [
        ("true", True),
        ("True", True),
        ("false", False),
        (True, True),
        (1, True)
    ]
)
def test_try_parse_bool(value, result):
    assert try_parse_bool(value) == result
