# H5P Injected Exercises

## All Types

- Unless otherwise stated, these properties are from the h5p's content.json file
- ids are generated from nickname, question index (for question sets), and answer index. Ids are known to be utilized in the follow places:
    - cookbook/lib/kitchen/injected_question_element.rb:81

### Collaborator Solutions

- These manifest as html elements with:
    - data-type="question-solution"
    - data-solution-source="collaborator"
    - data-solution-type="summary" or "detailed"
    - text comes from content_html which is what is described next
- detailed solution type: `detailedSolution` (if present)
- summary solution type: `summarySolution` (if present)
- Optional

### Formats

- These are included in the library definition in `nebuchadnezzar/nebu/h5p_injection.py`


## Multiple Choice

- stem_html: `question` (required)
- is_answer_order_important: `!behaviour.randomAnswers` (defaults to False)

### Answers

- content_html: `answer.text` (required)
- correctness: `answer.correct` (optional, defaults to false)
- feedback_html: `answer.tipsAndFeedback.chosenFeedback` (optional, omitted if not present)


## TrueFalse

- stem_html: `question` (required)
- is_answer_order_important: always `True`

### Answers

- content_html: True/False (generated)
- correctness: `correct` (optional)
- feedback_html: `feedbackOnCorrect` if the answer is correct, `feedbackOnWrong` if the answer is wrong, or omitted the correctness is unknown


## Essay

- stem_html: `taskDescription` (required)
- is_answer_order_important: always `False`

### Answers

- content_html: `keywords`
- correctness: always `True`
- feedback_html: `solution.introduction` (if present) joined to `solution.sample` (if present). (defaults to empty string)
