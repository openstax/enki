from typing import Literal, TypedDict


# TODO: Python 3.11 adds `NotRequired` for TypedDict which replaces this
# `total=...` + inheritance approach (we use 3.10 at the time of writing)
class ExerciseAnswerFull(TypedDict, total=False):
    correctness: str
    feedback_html: str


class ExerciseAnswer(ExerciseAnswerFull):
    id: str
    content_html: str


class CollaboratorSolution(TypedDict):
    content_html: str
    solution_type: Literal["detailed"] | Literal["summary"]


class ExerciseQuestionBase(TypedDict):
    id: str
    stem_html: str
    answers: list[ExerciseAnswer]
    is_answer_order_important: bool


class ExerciseQuestion(ExerciseQuestionBase):
    formats: list[str]
    collaborator_solutions: list[CollaboratorSolution]
