import logging
import os
import json
from pathlib import Path
from collections.abc import Callable
from typing import Any, NamedTuple
import traceback

from lxml import etree

from .utils import recursive_merge, try_parse_bool
from .typing.exercise import (
    ExerciseQuestion,
    ExerciseQuestionBase,
    ExerciseAnswer,
    CollaboratorSolution,
)


logger = logging.getLogger("nebuchadnezzar")


POSSIBLE_PROBLEMS = """\
Possible causes are:
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
            "\n" + POSSIBLE_PROBLEMS
        )


class UnsupportedLibraryError(H5PInjectionError):
    def __init__(self, library) -> None:
        super().__init__(library)


def _make_collaborator_solutions(entry) -> list[CollaboratorSolution]:
    return [
        {"content_html": entry[key], "solution_type": solution_type}
        for key, solution_type in (
            ("detailedSolution", "detailed"),
            ("summarySolution", "summary"),
        )
        if key in entry and len(entry[key]) > 0
    ]


def _answer_factory(
    content_html: str,
    correctness: bool | str | int | float | None,
    feedback_html: str | None,
) -> ExerciseAnswer:
    answer: ExerciseAnswer = {
        "content_html": content_html,
    }
    if correctness is not None:
        b_correctness = try_parse_bool(correctness)
        # cookbook/lib/kitchen/injected_question_element.rb:72
        answer["correctness"] = "1.0" if b_correctness else "0.0"
    if feedback_html is not None:
        answer["feedback_html"] = feedback_html
    return answer


def _question_factory(
    id_parts: list[str],
    stem_html: str,
    answers: list[ExerciseAnswer],
    is_answer_order_important: bool,
) -> ExerciseQuestionBase:
    return {
        "id": "_".join(id_parts),
        "stem_html": stem_html,
        "answers": answers,
        "is_answer_order_important": is_answer_order_important,
    }


def _multichoice_question_factory(id_parts: list[str], entry: dict[str, Any]):
    behavior = entry.get("behaviour", {})
    random_answers = try_parse_bool(behavior.get("randomAnswers", False))
    answers = [
        _answer_factory(
            content_html=answer["text"],
            correctness=answer.get("correct", None),
            feedback_html=answer.get("tipsAndFeedback", {}).get(
                "chosenFeedback", None
            ),
        )
        for answer in entry.get("answers", [])
    ]
    # Assertion disabled because many free-response multiple choice questions
    # have no answer choices
    # TODO: Maybe re-enable this check?
    # assert len(answers) > 0, NO_SOLUTION_ERROR
    return _question_factory(
        id_parts=id_parts,
        stem_html=entry["question"],
        answers=answers,
        is_answer_order_important=not random_answers,
    )


def _true_false_question_factory(id_parts: list[str], entry: dict[str, Any]):
    behavior = entry.get("behaviour", {})
    answers = []
    parsed_correctness = (
        try_parse_bool(entry["correct"]) if "correct" in entry else None
    )
    for option in (True, False):
        is_correct = parsed_correctness == option
        feedback_key = (
            "feedbackOnCorrect"
            if is_correct
            else "feedbackOnWrong"
            if parsed_correctness is not None
            else None
        )
        answers.append(
            _answer_factory(
                content_html=str(option),
                correctness=is_correct,
                feedback_html=behavior.get(feedback_key, None),
            )
        )
    return _question_factory(
        id_parts=id_parts,
        stem_html=entry["question"],
        answers=answers,
        is_answer_order_important=True,
    )


def _essay_question_factory(id_parts: list[str], entry: dict[str, Any]):
    keywords = entry.get("keywords", [])
    solution = entry.get("solution", {})
    solution_intro = solution.get("introduction", "")
    solution_sample = solution.get("sample", "")
    feedback = " ".join(v for v in (solution_intro, solution_sample) if v)
    answers = [
        _answer_factory(
            content_html=keyword["keyword"],
            correctness=True,
            feedback_html=feedback,
        )
        for keyword in keywords
        if keyword["keyword"] != "*"
    ]
    return _question_factory(
        id_parts=id_parts,
        stem_html=entry["taskDescription"],
        answers=answers,
        is_answer_order_important=False,
    )


class SupportedLibrary(NamedTuple):
    get_formats: Callable[[dict[str, Any]], list[str]]
    make_question: Callable[[list[str], dict[str, Any]], ExerciseQuestionBase]


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
    "H5P.Essay": SupportedLibrary(
        get_formats=lambda _: ["free-response"],
        make_question=_essay_question_factory,
    ),
}


def _add_question(
    id_parts: list[str],
    library: str,
    entry: dict[str, Any],
    questions: list[ExerciseQuestion],
):
    if library in SUPPORTED_LIBRARIES:
        lib = SUPPORTED_LIBRARIES[library]
        question: ExerciseQuestion = {
            **lib.make_question(id_parts, entry),
            "formats": lib.get_formats(entry),
            "collaborator_solutions": _make_collaborator_solutions(entry),
        }
        questions.append(question)
    elif library == "H5P.QuestionSet":
        for i, q in enumerate(entry["questions"]):
            sub_library = q["library"].split(" ")[0]
            sub_entry = q["params"]
            assert (
                sub_library != "H5P.QuestionSet"
            ), "Question sets cannot contain question sets"
            _add_question(
                [*id_parts, f"question{i + 1}"],
                sub_library,
                sub_entry,
                questions,
            )
    else:
        raise UnsupportedLibraryError(library)


def questions_from_h5p(
    nickname: str, h5p_in: dict[str, Any]
) -> list[ExerciseQuestion]:
    try:
        questions: list[ExerciseQuestion] = []
        main_library = h5p_in["h5p"]["mainLibrary"]
        _add_question([nickname], main_library, h5p_in["content"], questions)
        return questions
    except KeyError as ke:
        key = ke.args[0]
        raise H5PContentError(nickname, MISSING_PROPERTY_ERROR.format(key=key))
    except AssertionError as ae:
        underlying_error = ae.args[0]
        raise H5PContentError(nickname, underlying_error)


def tags_from_metadata(metadata: dict[str, Any]):
    tags = metadata.get("tags", [])
    tag_keys = [
        "assignment_type",
        "blooms",
        "dok",
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
                assert isinstance(
                    v, (str, int, bool, float)
                ), f"BUG: unsupported value: {k}"
                if k in {"aacn", "nclex"}:
                    add_tag("nursing", f"{k}:{v}")
                elif k == "name":
                    add_tag("book-slug", v)
                else:
                    add_tag(k, v)

    return tags


def load_h5p_interactive(
    interactive_path: str, private_path: str | None = None
):
    metadata_path = os.path.join(interactive_path, "metadata.json")
    content_path = os.path.join(interactive_path, "content.json")
    h5p_path = os.path.join(interactive_path, "h5p.json")
    if (
        not os.path.exists(metadata_path) or
        not os.path.exists(content_path) or
        not os.path.exists(h5p_path)
    ):
        logger.error(f"MISSING INTERACTIVE DATA: {interactive_path}")
        return None
    h5p = json.loads(Path(h5p_path).read_bytes())
    content = json.loads(Path(content_path).read_bytes())
    metadata = json.loads(Path(metadata_path).read_bytes())
    if private_path is not None:
        private_content_path = Path(private_path) / "content.json"
        content = recursive_merge(
            content, json.loads(private_content_path.read_bytes())
        )
    return {
        "h5p": h5p,
        "content": content,
        "metadata": metadata,
    }


def handle_attachments(
    attachments: list[str],
    nickname: str,
    node: etree.ElementBase,
    media_handler: Callable[[str, etree.ElementBase, str, bool], None],
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
