import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_GOLDEN_SET = Path("evals/golden_set.jsonl")
VALID_TYPES = {"lore", "mechanics", "strategy", "numeric"}


@dataclass(frozen=True)
class ValidationIssue:
    line_number: int
    case_id: str | None
    message: str


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[ValidationIssue]]:
    cases: list[dict[str, Any]] = []
    issues: list[ValidationIssue] = []

    if not path.exists():
        return cases, [ValidationIssue(0, None, f"file not found: {path}")]

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(line_number, None, f"invalid JSON: {exc.msg}"))
            continue
        if not isinstance(value, dict):
            issues.append(ValidationIssue(line_number, None, "case must be a JSON object"))
            continue
        cases.append(value)

    return cases, issues


def validate_case(case: dict[str, Any], line_number: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    case_id = case.get("id") if isinstance(case.get("id"), str) else None

    def add(message: str) -> None:
        issues.append(ValidationIssue(line_number, case_id, message))

    if not isinstance(case.get("id"), str) or not case["id"].strip():
        add("id must be a non-empty string")

    case_type = case.get("type")
    if case_type not in VALID_TYPES:
        add(f"type must be one of: {', '.join(sorted(VALID_TYPES))}")

    if not isinstance(case.get("question"), str) or not case["question"].strip():
        add("question must be a non-empty string")

    if not isinstance(case.get("reference_answer"), str) or not case["reference_answer"].strip():
        add("reference_answer must be a non-empty string")

    tags = case.get("tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
        add("tags must be a list of non-empty strings")

    if "needs_review" in case and not isinstance(case["needs_review"], bool):
        add("needs_review must be a boolean when present")

    if case_type == "numeric":
        has_value = "expected_value" in case and case["expected_value"] is not None
        has_label = isinstance(case.get("expected_label"), str) and case["expected_label"].strip()
        if not has_value and not has_label:
            add("numeric cases require expected_value or expected_label")
        if has_value and not isinstance(case["expected_value"], (int, float)):
            add("expected_value must be a number")
        if has_value:
            if "tolerance" not in case:
                add("numeric cases with expected_value require tolerance")
            elif not isinstance(case["tolerance"], (int, float)) or case["tolerance"] < 0:
                add("tolerance must be a non-negative number")

    return issues


def validate_cases(cases: list[dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: dict[str, int] = {}

    for index, case in enumerate(cases, 1):
        issues.extend(validate_case(case, index))
        case_id = case.get("id")
        if isinstance(case_id, str) and case_id.strip():
            if case_id in seen:
                issues.append(
                    ValidationIssue(index, case_id, f"duplicate id; first seen on line {seen[case_id]}")
                )
            else:
                seen[case_id] = index

    return issues


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts = Counter(case.get("type", "unknown") for case in cases)
    tag_counts = Counter(tag for case in cases for tag in case.get("tags", []))
    needs_review = sum(1 for case in cases if case.get("needs_review") is True)
    return {
        "total": len(cases),
        "types": dict(sorted(type_counts.items())),
        "top_tags": dict(tag_counts.most_common(12)),
        "needs_review": needs_review,
    }


def print_issues(issues: list[ValidationIssue]) -> None:
    for issue in issues:
        location = f"line {issue.line_number}" if issue.line_number else "file"
        case = f" [{issue.case_id}]" if issue.case_id else ""
        print(f"{location}{case}: {issue.message}")


def print_stats(cases: list[dict[str, Any]]) -> None:
    summary = summarize(cases)
    print(f"Total: {summary['total']}")
    print(f"Needs review: {summary['needs_review']}")
    print("Types:")
    for case_type, count in summary["types"].items():
        print(f"  {case_type}: {count}")
    print("Top tags:")
    for tag, count in summary["top_tags"].items():
        print(f"  {tag}: {count}")


def print_case_list(cases: list[dict[str, Any]]) -> None:
    for case in cases:
        marker = "review" if case.get("needs_review") else "ready"
        print(f"{case['id']} [{case['type']}, {marker}] {case['question']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline eval utilities for Deadlock RAG.")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument("--validate", action="store_true", help="Validate the JSONL schema.")
    parser.add_argument("--stats", action="store_true", help="Print golden-set coverage stats.")
    parser.add_argument("--list", action="store_true", help="List eval case IDs and questions.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases, load_issues = load_jsonl(args.golden_set)
    validation_issues = validate_cases(cases)
    issues = load_issues + validation_issues

    if args.validate or not (args.stats or args.list):
        if issues:
            print_issues(issues)
            return 1
        print(f"OK: {len(cases)} eval cases in {args.golden_set}")

    if issues:
        print_issues(issues)
        return 1

    if args.stats:
        print_stats(cases)

    if args.list:
        print_case_list(cases)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
