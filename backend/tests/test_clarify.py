"""Parsing of the structured clarifying-question block."""
from __future__ import annotations

from app.core.clarify import MAX_QUESTIONS, parse_questions
from app.services.chat_service import compose_user_text
from app.schemas.chat import ClarifyAnswer


def test_parses_block_and_strips_it_from_the_text():
    reply = (
        "Thanks for telling me. I need two details.\n\n"
        '<questions>[{"question": "When were you dismissed?", '
        '"choices": ["This week", "Earlier"]}, '
        '{"question": "Was it in writing?", "choices": ["Yes", "No"]}]</questions>'
    )
    text, questions = parse_questions(reply)
    assert "<questions>" not in text
    assert text.endswith("two details.")
    assert [q["question"] for q in questions] == [
        "When were you dismissed?",
        "Was it in writing?",
    ]
    assert questions[0]["choices"] == ["This week", "Earlier"]


def test_bare_array_without_tags_is_still_parsed():
    text, questions = parse_questions(
        'Ok.\n[{"question": "Which city?", "choices": ["Munich", "Berlin"]}]'
    )
    assert text == "Ok."
    assert len(questions) == 1


def test_model_supplied_other_choice_is_dropped():
    _, questions = parse_questions(
        '<questions>[{"question": "Which?", '
        '"choices": ["A", "B", "Other", "Not sure"]}]</questions>'
    )
    assert questions[0]["choices"] == ["A", "B"]


def test_caps_and_dedupes():
    items = ", ".join(
        f'{{"question": "Q{i}", "choices": ["a", "b", "c", "d", "e", "f"]}}'
        for i in range(8)
    )
    _, questions = parse_questions(f"<questions>[{items}]</questions>")
    assert len(questions) == MAX_QUESTIONS
    assert len(questions[0]["choices"]) == 5

    _, dupes = parse_questions(
        '<questions>[{"question": "Same?", "choices": ["a", "b"]}, '
        '{"question": "same?", "choices": ["c", "d"]}]</questions>'
    )
    assert len(dupes) == 1


def test_malformed_block_is_discarded_not_shown():
    text, questions = parse_questions("Here you go.\n<questions>{not json</questions>")
    assert questions == []
    assert "not json" not in text


def test_plain_reply_is_untouched():
    text, questions = parse_questions("A summary with no questions.")
    assert text == "A summary with no questions."
    assert questions == []


def test_answers_compose_into_one_user_turn():
    composed = compose_user_text(
        "",
        [
            ClarifyAnswer(question="When?", answer="This week"),
            ClarifyAnswer(question="In writing?", answer=None),
        ],
    )
    assert "When?" in composed and "This week" in composed
    assert "(skipped)" in composed
    assert "skipped these questions" not in composed


def test_all_skipped_tells_the_model_not_to_re_ask():
    composed = compose_user_text(
        "", [ClarifyAnswer(question="When?", answer=None)]
    )
    assert "skipped these questions" in composed


def test_recovers_questions_the_model_wrote_as_prose():
    """A smaller model sometimes ignores the block and writes
    "- Do you have X? (Yes / No)". The choices are recovered rather than
    left as text the user has to answer by typing."""
    reply = (
        "To help you prepare that summary, I still need two things:\n\n"
        "- Do you still have a copy of your employment contract?\n"
        "(Yes, I have it / No, I don't have it / I think I have it but need to look)\n"
        "- What country were you employed in?\n\n"
        "Once you answer these, I can draft a clean factual summary."
    )
    text, questions = parse_questions(reply)
    assert [q["question"] for q in questions] == [
        "Do you still have a copy of your employment contract?",
        "What country were you employed in?",
    ]
    assert questions[0]["choices"] == [
        "Yes, I have it",
        "No, I don't have it",
        "I think I have it but need to look",
    ]
    # A question with no options is still asked — as a free-text prompt.
    assert questions[1]["choices"] == []
    # The lines are lifted out of the visible reply, gap and all.
    assert "Do you still have" not in text
    assert text.startswith("To help you prepare")
    assert text.endswith("factual summary.")
    assert "\n\n\n" not in text


def test_an_ordinary_closing_question_is_left_alone():
    """Without slash-separated options there is nothing to turn into
    choices, so the reply stays exactly as written."""
    reply = "Thanks for explaining. What happened after the meeting?"
    text, questions = parse_questions(reply)
    assert questions == []
    assert text == reply


def test_a_broken_block_falls_back_to_the_prose_it_contains():
    reply = (
        "I need one thing:\n\n"
        "- Do you have the letter? (Yes / No)\n\n"
        "<questions>{ oops not json</questions>"
    )
    text, questions = parse_questions(reply)
    assert [q["choices"] for q in questions] == [["Yes", "No"]]
    assert "oops" not in text
