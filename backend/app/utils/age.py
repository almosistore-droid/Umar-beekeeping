"""Queen age: computed from birth date (or birth year), never stored."""
from datetime import date


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def age_in_months(birth_date: date | None, birth_year: int | None, today: date) -> int | None:
    """Full months of age. With only a birth year we assume mid-year (1 July)."""
    if birth_date is None and birth_year is None:
        return None
    born = birth_date or date(birth_year, 7, 1)
    months = (today.year - born.year) * 12 + (today.month - born.month)
    if today.day < born.day:
        months -= 1
    return max(months, 0)


def age_label(birth_date: date | None, birth_year: int | None, today: date) -> str | None:
    """'2 года 3 месяца'; prefixed with '≈' when only the year is known."""
    months = age_in_months(birth_date, birth_year, today)
    if months is None:
        return None
    years, rest = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} {plural_ru(years, 'год', 'года', 'лет')}")
    if rest or not years:
        parts.append(f"{rest} {plural_ru(rest, 'месяц', 'месяца', 'месяцев')}")
    label = " ".join(parts)
    return label if birth_date else f"≈ {label}"
