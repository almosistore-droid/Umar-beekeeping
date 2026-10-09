from datetime import date

import pytest

from app.utils.age import age_in_months, age_label, plural_ru


def test_spec_example():
    # Spec: born 15.06.2024, today 06.10.2026 -> "2 года 3 месяца"
    assert age_label(date(2024, 6, 15), 2024, date(2026, 10, 6)) == "2 года 3 месяца"


@pytest.mark.parametrize(
    "born, today, months, label",
    [
        (date(2026, 9, 6), date(2026, 10, 6), 1, "1 месяц"),
        (date(2026, 9, 7), date(2026, 10, 6), 0, "0 месяцев"),
        (date(2025, 10, 6), date(2026, 10, 6), 12, "1 год"),
        (date(2021, 4, 1), date(2026, 10, 6), 66, "5 лет 6 месяцев"),
        (date(2024, 2, 29), date(2026, 2, 28), 23, "1 год 11 месяцев"),
    ],
)
def test_ages(born, today, months, label):
    assert age_in_months(born, None, today) == months
    assert age_label(born, None, today) == label


def test_only_year_is_approximate():
    assert age_label(None, 2024, date(2026, 10, 6)) == "≈ 2 года 3 месяца"


def test_unknown_age():
    assert age_in_months(None, None, date(2026, 1, 1)) is None
    assert age_label(None, None, date(2026, 1, 1)) is None


@pytest.mark.parametrize("n, word", [(1, "год"), (2, "года"), (5, "лет"), (11, "лет"), (21, "год"), (22, "года")])
def test_plural(n, word):
    assert plural_ru(n, "год", "года", "лет") == word
