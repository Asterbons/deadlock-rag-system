import re
from dataclasses import dataclass
from typing import Any


NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:,\d{3})+|\d+)(?:\.\d+)?")


@dataclass(frozen=True)
class AssertionResult:
    passed: bool
    reason: str
    details: dict[str, Any]


def extract_numbers(text: str) -> list[float]:
    """Extract decimal numbers from free-form model output."""
    values: list[float] = []
    for match in NUMBER_RE.findall(text):
        normalized = match.replace(",", "")
        try:
            values.append(float(normalized))
        except ValueError:
            continue
    return values


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def contains_label(answer: str, expected_label: str) -> bool:
    return normalize_label(expected_label) in normalize_label(answer)


def check_numeric_answer(
    answer: str,
    *,
    expected_value: float | int | None = None,
    tolerance: float | int | None = None,
    expected_label: str | None = None,
) -> AssertionResult:
    """Check numeric eval output using value tolerance and/or label containment."""
    checks: dict[str, Any] = {}

    if expected_value is None and expected_label is None:
        return AssertionResult(
            passed=False,
            reason="numeric case has no expected_value or expected_label",
            details=checks,
        )

    if expected_label is not None:
        label_passed = contains_label(answer, expected_label)
        checks["label"] = {
            "expected": expected_label,
            "passed": label_passed,
        }
    else:
        label_passed = True

    if expected_value is not None:
        effective_tolerance = 0 if tolerance is None else float(tolerance)
        numbers = extract_numbers(answer)
        closest = min(numbers, key=lambda value: abs(value - float(expected_value))) if numbers else None
        value_passed = (
            closest is not None
            and abs(closest - float(expected_value)) <= effective_tolerance
        )
        checks["value"] = {
            "expected": float(expected_value),
            "tolerance": effective_tolerance,
            "actual_candidates": numbers,
            "closest": closest,
            "passed": value_passed,
        }
    else:
        value_passed = True

    passed = label_passed and value_passed
    return AssertionResult(
        passed=passed,
        reason="passed" if passed else "answer did not match expected numeric constraints",
        details=checks,
    )
