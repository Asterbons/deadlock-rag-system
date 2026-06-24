from scripts.eval_asserts import check_numeric_answer, extract_numbers


def test_extract_numbers_handles_commas_and_decimals():
    assert extract_numbers("Health is 1,240 and cooldown is 6.5s") == [1240.0, 6.5]


def test_check_numeric_answer_passes_when_any_number_is_within_tolerance():
    result = check_numeric_answer(
        "The answer is Infernus with 839.8 health.",
        expected_value=840,
        tolerance=0.5,
        expected_label="Infernus",
    )

    assert result.passed is True
    assert result.details["value"]["closest"] == 839.8


def test_check_numeric_answer_fails_missing_expected_label():
    result = check_numeric_answer(
        "Abrams has 810 health.",
        expected_value=810,
        tolerance=0,
        expected_label="Infernus",
    )

    assert result.passed is False
    assert result.details["label"]["passed"] is False


def test_check_numeric_answer_requires_at_least_one_constraint():
    result = check_numeric_answer("Any answer")

    assert result.passed is False
    assert "no expected_value or expected_label" in result.reason
