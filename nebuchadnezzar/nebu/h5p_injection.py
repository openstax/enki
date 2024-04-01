import logging
import os
import json
from pathlib import Path
from typing import Any, Callable, List, NamedTuple, Union
import traceback

from lxml import etree

from .utils import recursive_merge, try_parse_bool


logger = logging.getLogger("nebuchadnezzar")


POSSIBLE_PROBLEMS = """\
Possible causes are:
- Private content may not have been fetched
- The private content may be in the wrong format
- The content may be malformed
"""

MISSING_PROPERTY_ERROR = (
    "Content was missing the following required property: {key}"
)

NO_SOLUTION_ERROR = "Content was missing solution."


class H5PInjectionError(Exception):
    pass


class H5PContentError(H5PInjectionError):
    def __init__(self, nickname, error) -> None:
        super().__init__(
            "H5P content injection error\n\n"
            f"H5P Content ID: {nickname}\n"
            f"{error}\n"
            "\n" +
            POSSIBLE_PROBLEMS
        )


class UnsupportedLibraryError(H5PInjectionError):
    def __init__(self, library) -> None:
        super().__init__(library)


def _make_collaborator_solutions(entry):
    return [
        {
            "content_html": entry[key],
            "solution_type": solution_type
        }
        for key, solution_type in (
            ("detailedSolution", "detailed"),
            ("summarySolution", "summary")
        )
        if key in entry and len(entry[key]) > 0
    ]


def _answer_factory(
    id: int,
    content_html: str,
    correctness: Union[bool, str, int, float],
    feedback_html: str
) -> dict[str, Any]:
    b_correctness = try_parse_bool(correctness)
    return {
        "id": id,
        "content_html": content_html,
        # cookbook/lib/kitchen/injected_question_element.rb#L72
        "correctness": "1.0" if b_correctness else "0.0",
        "feedback_html": feedback_html,
    }


def _question_factory(
    id: int,
    stem_html: str,
    answers: List[dict[str, Any]],
    is_answer_order_important: bool
) -> dict[str, Any]:
    return {
        "id": id,
        "stem_html": stem_html,
        "answers": answers,
        "is_answer_order_important": is_answer_order_important,
    }


def _multichoice_question_factory(id: int, entry: dict[str, Any]):
    behavior = entry.get("behaviour", {})
    random_answers = try_parse_bool(behavior.get("randomAnswers", False))
    answers = [
        _answer_factory(
            id=index + 1,
            content_html=answer["text"],
            correctness=answer["correct"],
            feedback_html=answer["tipsAndFeedback"]["chosenFeedback"],
        )
        for index, answer in enumerate(entry["answers"])
    ]
    assert len(answers) > 0, NO_SOLUTION_ERROR
    return _question_factory(
        id=id,
        stem_html=entry["question"],
        answers=answers,
        is_answer_order_important=not random_answers
    )


def _true_false_question_factory(id: int, entry: dict[str, Any]):
    behavior = entry.get("behaviour", {})
    answers = []
    parsed_correctness = try_parse_bool(entry["correct"])
    for index, option in enumerate((True, False)):
        is_correct = parsed_correctness == option
        feedback_key = (
            "feedbackOnCorrect"
            if is_correct
            else "feedbackOnWrong"
        )
        answers.append(
            _answer_factory(
                id=index + 1,
                content_html=str(option),
                correctness=is_correct,
                feedback_html=behavior.get(feedback_key, ""),
            )
        )
    return _question_factory(
        id=id,
        stem_html=entry["question"],
        answers=answers,
        is_answer_order_important=True,
    )


class SupportedLibrary(NamedTuple):
    get_formats: Callable[[dict[str, Any]], List[str]]
    make_question: Callable[[int, dict[str, Any]], dict[str, Any]]


SUPPORTED_LIBRARIES = {
    "H5P.MultiChoice": SupportedLibrary(
        get_formats=lambda q: (
            ["free-response", "multiple-choice"]
            if q.get("isFreeResponseSupported", False) is True
            else ["multiple-choice"]
        ),
        make_question=_multichoice_question_factory,
    ),
    "H5P.TrueFalse": SupportedLibrary(
        get_formats=lambda _: ["true-false"],
        make_question=_true_false_question_factory,
    ),
}


def _add_question(
    id: int,
    library: str,
    entry: dict[str, Any],
    questions: List[dict[str, Any]] = [],
):
    question = {}
    if library in SUPPORTED_LIBRARIES:
        lib = SUPPORTED_LIBRARIES[library]
        question["formats"] = lib.get_formats(entry)
        question.update(**lib.make_question(id, entry))
        question["collaborator_solutions"] = _make_collaborator_solutions(
            entry
        )
        if entry.get("isSolutionPublic", None) is not True:
            question["answers"] = [
                {
                    k: v
                    for k, v in answer.items()
                    if k not in ("correctness", "feedback_html")
                }
                for answer in question["answers"]
            ]
            question["collaborator_solutions"] = []
        questions.append(question)
    elif library == "H5P.QuestionSet":
        for i, q in enumerate(entry["questions"]):
            sub_library = q["library"].split(" ")[0]
            sub_entry = q["params"]
            assert sub_library != "H5P.QuestionSet", \
                "Question sets cannot contain question sets"
            _add_question(i + 1, sub_library, sub_entry, questions)
    else:
        raise UnsupportedLibraryError(library)


def questions_from_h5p(nickname: str, h5p_in: dict[str, Any]):
    try:
        questions = []
        main_library = h5p_in["h5p"]["mainLibrary"]
        _add_question(1, main_library, h5p_in["content"], questions)
        return questions
    except KeyError as ke:
        key = ke.args[0]
        raise H5PContentError(
            nickname, MISSING_PROPERTY_ERROR.format(key=key)
        )
    except AssertionError as ae:
        underlying_error = ae.args[0]
        raise H5PContentError(nickname, underlying_error)


def tags_from_metadata(metadata: dict[str, Any]):
    tags = metadata.get("tags", [])
    tag_keys = [
        "assignment_type",
        "blooms",
        "dok",
        "feature_page",
        "feature_id",
        "time",
    ]

    def add_tag(name, value):
        name = name.replace("_", "-")
        tags.append(f"{name}:{value}")

    for k in filter(lambda k: k in metadata, tag_keys):
        add_tag(k, metadata[k])

    for book in metadata.get("books", []):
        b = book["name"]
        for k, v in book.items():
            if k in {"lo", "aplo"}:
                assert isinstance(v, list), f"BUG: {k} should be a list"
                for sub_v in v:
                    add_tag(k, f"{b}:{sub_v}")
            else:
                assert isinstance(v, (str, int, bool, float)), \
                    f"BUG: unsupported value: {k}"
                if k in {"aacn", "nclex"}:
                    add_tag("nursing", f"{k}:{v}")
                elif k == "name":
                    add_tag("book-slug", v)
                else:
                    add_tag(k, v)

    return tags


def load_h5p_interactive(interactive_path: str, private_path: str):
    metadata_path = os.path.join(interactive_path, "metadata.json")
    content_path = os.path.join(interactive_path, "content.json")
    h5p_path = os.path.join(interactive_path, "h5p.json")
    private_metadata_path = os.path.join(private_path, "metadata.json")
    private_content_path = os.path.join(private_path, "content.json")
    if (
        not os.path.exists(metadata_path) or
        not os.path.exists(content_path) or
        not os.path.exists(h5p_path)
    ):
        logger.error(f"MISSING INTERACTIVE DATA: {interactive_path}")
        return None
    h5p_in = {}
    h5p_in["h5p"] = json.loads(Path(h5p_path).read_bytes())
    h5p_in["content"] = recursive_merge(
        json.loads(Path(content_path).read_bytes()),
        json.loads(Path(private_content_path).read_bytes())
        if os.path.exists(private_content_path)
        else {},
    )
    h5p_in["metadata"] = recursive_merge(
        json.loads(Path(metadata_path).read_bytes()),
        json.loads(Path(private_metadata_path).read_bytes())
        if os.path.exists(private_metadata_path)
        else {},
    )
    return h5p_in


def handle_attachments(
    attachments: List[str],
    nickname: str,
    node: etree.ElementBase,
    media_handler: Callable[[str, etree.ElementBase, str, bool], None]
):
    # The idea is to be relatively generic with the xpath and handle
    # results conditionally in the loop
    # No namespaces at this point (except when they have been included
    # in the H5P content like for math), so names should be mostly local
    for media_elem in node.xpath(
        '//img[@src][not(starts-with(@src, "http"))] |'
        '//audio[@src][not(starts-with(@src, "http"))] |'
        '//video//source[@src][not(starts-with(@src, "http"))]'
    ):
        attrib = "src"
        is_image = media_elem.tag == "img"
        uri = media_elem.attrib[attrib]
        fq_uri = f"{nickname}:{uri}"
        if uri not in attachments:  # pragma: no cover
            logger.warning(f"Resource not found in H5P attachments: {fq_uri}")
        try:
            media_handler(nickname, media_elem, attrib, is_image)
        except Exception as e:  # pragma: no cover
            logger.error(f"Error while handling resource file ({fq_uri}):")
            for tb in traceback.format_exception(e):
                logger.error(tb)
