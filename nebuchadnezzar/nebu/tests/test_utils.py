import json

from nebu.utils import recursive_merge


def test_recursive_merge_dict():
    a = {"x": 1, "y": [2], "z": {"w": [1]}}
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
    assert merged["y"] == [2, 3]
    # Default: recursively merge dicts
    assert merged["z"]["w"] == [1, 2]
    # Override default behavior to add int and/or float
    custom_default = recursive_merge(
        a,
        b,
        default=lambda a, b: a + b if isinstance(a, (int, float)) else b
    )
    assert custom_default["x"] == 3
