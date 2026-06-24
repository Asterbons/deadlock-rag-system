from pathlib import Path

from scripts.run_eval import load_jsonl, summarize, validate_cases


def test_golden_set_schema_is_valid():
    cases, load_issues = load_jsonl(Path("evals/golden_set.jsonl"))

    assert load_issues == []
    assert validate_cases(cases) == []
    assert len(cases) >= 10


def test_validate_cases_rejects_duplicate_ids():
    cases = [
        {
            "id": "duplicate",
            "type": "strategy",
            "question": "Question?",
            "reference_answer": "Answer.",
            "tags": ["strategy"],
            "needs_review": True,
        },
        {
            "id": "duplicate",
            "type": "strategy",
            "question": "Another question?",
            "reference_answer": "Another answer.",
            "tags": ["strategy"],
            "needs_review": True,
        },
    ]

    issues = validate_cases(cases)

    assert any("duplicate id" in issue.message for issue in issues)


def test_validate_cases_requires_numeric_expectation():
    cases = [
        {
            "id": "numeric_bad",
            "type": "numeric",
            "question": "What is the value?",
            "reference_answer": "Expected answer.",
            "tags": ["numeric"],
            "needs_review": False,
        }
    ]

    issues = validate_cases(cases)

    assert any("expected_value or expected_label" in issue.message for issue in issues)


def test_summarize_counts_types_tags_and_review_flags():
    cases = [
        {
            "id": "a",
            "type": "strategy",
            "question": "Question?",
            "reference_answer": "Answer.",
            "tags": ["strategy", "retrieval_required"],
            "needs_review": True,
        },
        {
            "id": "b",
            "type": "numeric",
            "question": "Question?",
            "reference_answer": "Answer.",
            "expected_label": "Infernus",
            "tags": ["numeric", "tool_required"],
            "needs_review": False,
        },
    ]

    summary = summarize(cases)

    assert summary["total"] == 2
    assert summary["types"] == {"numeric": 1, "strategy": 1}
    assert summary["needs_review"] == 1
    assert summary["top_tags"]["strategy"] == 1
