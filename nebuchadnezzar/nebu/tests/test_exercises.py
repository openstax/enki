import json
from copy import copy
import re

import pytest
from nebu.formatters import exercise_callback_factory, fetch_insert_includes
from nebu.models.book_part import BookPart, PartType
from nebu.xml_utils import etree_from_str, fix_namespaces


EXERCISE_URL = "https://exercises.openstax.org/api/exercises?q=tag:{itemCode}"
EXERCISE_JSON_HTML = {
    "items": [
        {
            "uid": "93@3",
            "group_uuid": "e071207a-9d26-4cff-bbe9-9060d3d13ca6",
            "copyright_holders": [{"user_id": 2, "name": "Rice University"}],
            "uuid": "8fa80526-0720-4a98-99c8-5d6113482424",
            "authors": [{"user_id": 1, "name": "OpenStax"}],
            "published_at": "2016-09-16T17:40:20.497Z",
            "number": 93,
            "editors": [],
            "is_vocab": False,
            "stimulus_html": "<p>Please answer the following question:</p>",
            "questions": [
                {
                    "stimulus_html": "",
                    "formats": ["free-response", "multiple-choice"],
                    "hints": [],
                    "id": 63062,
                    "is_answer_order_important": True,
                    "answers": [
                        {
                            "id": 259956,
                            "content_html": "monomers",
                            "correctness": "0.0",
                        },
                        {
                            "content_html": "polymers (<span data-math='retry' />)",
                            "id": 259957,
                            "correctness": "1.0",
                        },
                        {
                            "id": 259958,
                            "content_html": "carbohydrates only (<span data-math='' />)",
                            "correctness": "0.0",
                        },
                        {
                            "content_html": "water only (<span data-math='\\text{H}_2\\text{O}'>\\text{H}_2\\text{O}</span>)",
                            "id": 259959,
                            "correctness": "0.0",
                        },
                        {
                            "content_html": "polymer and water (<div data-math='\\text{H}_2\\text{O}'>\\text{H}_2\\text{O}</div>)",
                            "id": 259959,
                            "correctness": "1.0",
                        },
                    ],
                    "combo_choices": [],
                    "stem_html": "Dehydration <img href='none'> synthesis leads to the formation of what?",
                }
            ],
            "tags": [
                "apbio",
                "inbook-yes",
                "ost-chapter-review",
                "review",
                "apbio-ch03",
                "apbio-ch03-s01",
                "apbio-ch03-s01-lo01",
                "apbio-ch03-ex002",
                "dok:1",
                "blooms:1",
                "time:short",
                "book:stax-bio",
                "context-cnxmod:ea44b8fa-e7a2-4360-ad34-ac081bcf104f",
                "exid:apbio-ch03-ex002",
                "context-cnxmod:85d6c500-9860-42e8-853a-e6940a50224f",
                "book:stax-apbio",
                "filter-type:import:hs",
                "type:conceptual-or-recall",
            ],
            "derived_from": [],
            "version": 3,
        }
    ],
    "total_count": 1,
}

EXERCISE_JSON = {
    "items": [
        {
            "uid": "93@3",
            "group_uuid": "e071207a-9d26-4cff-bbe9-9060d3d13ca6",
            "copyright_holders": [{"user_id": 2, "name": "Rice University"}],
            "uuid": "8fa80526-0720-4a98-99c8-5d6113482424",
            "authors": [{"user_id": 1, "name": "OpenStax"}],
            "published_at": "2016-09-16T17:40:20.497Z",
            "number": 93,
            "editors": [],
            "is_vocab": False,
            "stimulus_html": "",
            "questions": [
                {
                    "stimulus_html": "Here's an excerpt please read",
                    "formats": ["free-response", "multiple-choice"],
                    "hints": [],
                    "id": 63062,
                    "is_answer_order_important": True,
                    "answers": [
                        {"id": 259956, "content_html": "monomers"},
                        {"content_html": "polymers", "id": 259957},
                        {"id": 259958, "content_html": "carbohydrates only"},
                        {"content_html": "water only", "id": 259959},
                    ],
                    "combo_choices": [],
                    "stem_html": "Dehydration <img href='none'/> synthesis leads to the formation of what?",
                }
            ],
            "tags": [
                "apbio",
                "inbook-yes",
                "ost-chapter-review",
                "review",
                "apbio-ch03",
                "apbio-ch03-s01",
                "apbio-ch03-s01-lo01",
                "apbio-ch03-ex002",
                "dok:1",
                "blooms:1",
                "time:short",
                "book:stax-bio",
                "context-cnxmod:ea44b8fa-e7a2-4360-ad34-ac081bcf104f",
                "exid:apbio-ch03-ex002",
                "context-cnxmod:85d6c500-9860-42e8-853a-e6940a50224f",
                "context-cnxmod:lemon",
                "book:stax-apbio",
                "filter-type:import:hs",
                "type:conceptual-or-recall",
                "context-cnxfeature:link-to-feature-2",
            ],
            "derived_from": [],
            "version": 3,
        }
    ],
    "total_count": 1,
}

BAD_EQUATION_JSON = {
    "error": "E_VALIDATION",
    "status": 400,
    "summary": "1 attribute is invalid",
    "model": "Equation",
    "invalidAttributes": {
        "math": [
            {
                "rule": "required",
                "message": "\"required\" validation rule failed for input: ''\nSpecifically, it threw an error.  Details:\n undefined",
            }
        ]
    },
}


EQUATION_JSON = {
    "updatedAt": "2016-10-31T16:06:44.413Z",
    "cloudUrl": "https://mathmlcloud.cnx.org:1337/equation/58176c14d08360010084f48c",
    "mathType": "TeX",
    "math": "\\text{H}_2\\text{O}",
    "components": [
        {
            "format": "mml",
            "equation": "58176c14d08360010084f48c",
            "source": '<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">\n  <msub>\n    <mtext>H</mtext>\n    <mn>2</mn>\n  </msub>\n  <mtext>O</mtext>\n</math>',
            "updatedAt": "2016-10-31T16:06:44.477Z",
            "id": "58176c14d08360010084f48d",
            "createdAt": "2016-10-31T16:06:44.477Z",
        }
    ],
    "submittedBy": None,
    "ip_address": "::ffff:10.64.71.226",
    "id": "58176c14d08360010084f48c",
    "createdAt": "2016-10-31T16:06:44.413Z",
}


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.text = json.dumps(json_data)
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.fixture
def current_snapshot_dir(snapshot_dir):
    return snapshot_dir / "exercises"


@pytest.fixture(autouse=True)
def patch_requests(monkeypatch):
    url = "https://exercises.openstax.org/api/exercises?q=tag:apbio-ch03-ex002"

    def mocked_requests_get(*args, **kwargs):
        if args[0] == url:
            if "headers" in kwargs:
                assert kwargs["headers"] == {
                    "Authorization": "Bearer somesortoftoken"
                }
                return MockResponse(EXERCISE_JSON_HTML, 200)
            return MockResponse(EXERCISE_JSON, 200)

        else:
            return MockResponse({"total_count": 0, "items": []}, 200)

    def mocked_requests_post(*args, **kwargs):
        if args[0].startswith("http://mathmlcloud.cnx.org/equation"):
            if args[1]["math"] == b"\\text{H}_2\\text{O}":
                return MockResponse(EQUATION_JSON, 200)
            elif args[1]["math"] == b"retry":
                return MockResponse("{}", 200)
            elif args[1]["math"] == b"":
                return MockResponse(BAD_EQUATION_JSON, 400)
            else:
                return MockResponse("", 500)
        return MockResponse({}, 404)

    monkeypatch.setattr("nebu.formatters.requests.get", mocked_requests_get)
    monkeypatch.setattr("nebu.formatters.requests.post", mocked_requests_post)


def mocked_requests_post(*args, **kwargs):
    if args[0].startswith("http://mathmlcloud.cnx.org/equation"):
        if args[1]["math"] == b"\\text{H}_2\\text{O}":
            return MockResponse(EQUATION_JSON, 200)
        elif args[1]["math"] == b"retry":
            return MockResponse("{}", 200)
        elif args[1]["math"] == b"":
            return MockResponse(BAD_EQUATION_JSON, 400)
        else:
            return MockResponse("", 500)
    return MockResponse({}, 404)


@pytest.fixture
def fake_doc(datadir):
    return BookPart(
        type=PartType.DOCUMENT,
        metadata={"uuid": ""},
        content=etree_from_str(
            (datadir / "desserts-single-page.xhtml").read_bytes()
        ),
    )


def test_includes_callback(assert_match, fake_doc):
    def _upcase_text(elem, page_uuids=None):
        if elem.text:
            elem.text = elem.text.upper()
        for child in elem.iterdescendants():
            if child.text:
                child.text = child.text.upper()
            if child.tail:
                child.tail = child.tail.upper()

    exercise_match = "#ost/api/ex/"

    includes = [
        exercise_callback_factory(exercise_match, EXERCISE_URL),
        ('//xhtml:*[@data-type = "exercise"]', _upcase_text),
        ("//xhtml:a", _upcase_text),
    ]

    fetch_insert_includes(fake_doc, [""], includes)
    assert_match(fix_namespaces(fake_doc.content), "document.xhtml")


def test_includes_token_callback(assert_match, fake_doc):
    def _upcase_text(elem, page_uuids=None):
        if elem.text:
            elem.text = elem.text.upper()
        for child in elem.iterdescendants():
            if child.text:
                child.text = child.text.upper()
            if child.tail:
                child.tail = child.tail.upper()

    exercise_match = "#ost/api/ex/"
    exercise_token = "somesortoftoken"

    includes = [
        exercise_callback_factory(
            exercise_match, EXERCISE_URL, exercise_token
        ),
        ('//xhtml:*[@data-type = "exercise"]', _upcase_text),
        ("//xhtml:a", _upcase_text),
    ]

    fetch_insert_includes(fake_doc, ["", "123", "456"], includes)
    assert_match(fix_namespaces(fake_doc.content), "document.xhtml")


def test_no_tags(assert_match, fake_doc, monkeypatch):
    def exercise_no_tags(*args, **kwargs):
        tagless = copy(EXERCISE_JSON)
        tagless["items"][0]["tags"] = []
        return MockResponse(tagless, 200)

    exercise_match = "#ost/api/ex/"

    includes = [exercise_callback_factory(exercise_match, EXERCISE_URL, None)]

    monkeypatch.setattr("nebu.formatters.requests.get", exercise_no_tags)

    fetch_insert_includes(fake_doc, [""], includes)
    assert_match(fix_namespaces(fake_doc.content), "document.xhtml")


def test_feature(assert_match, fake_doc, monkeypatch):
    def exercise_mod_tags(*args, **kwargs):
        mod_tags = copy(EXERCISE_JSON_HTML)
        mod_tags["items"][0]["tags"] = [
            "context-cnxfeature:i-made-this-up",  # if maybe_feature is None
            "context-cnxmod:a",  # target_module = candidate_uuids.pop()
        ]
        return MockResponse(mod_tags, 200)

    exercise_match = "#ost/api/ex/"

    includes = [exercise_callback_factory(exercise_match, EXERCISE_URL, None)]

    monkeypatch.setattr("nebu.formatters.requests.get", exercise_mod_tags)

    with pytest.raises(Exception) as e:
        fetch_insert_includes(fake_doc, ["a", "b", "c"], includes)
        assert len(re.findall(r"Feature .+? not in .+? href=.+?", str(e))) == 4
