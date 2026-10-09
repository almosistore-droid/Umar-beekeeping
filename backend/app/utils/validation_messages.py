"""Translate Pydantic validation errors into short Russian messages."""
from typing import Any

FIELD_LABELS = {
    "name": "Название", "hive_number": "Номер улья", "hive_type": "Тип улья", "status": "Статус",
    "apiary_id": "Пасека", "queen_code": "Код матки", "birth_date": "Дата рождения",
    "birth_year": "Год рождения", "latitude": "Широта", "longitude": "Долгота",
    "strength": "Сила семьи", "origin": "Происхождение", "start_date": "Дата заселения",
    "installation_date": "Дата установки", "colonization_date": "Дата заселения",
    "egg_laying_quality": "Яйценоскость", "swarming_tendency": "Ройливость",
    "temperament": "Миролюбие", "queen_id": "Матка", "init_data": "Данные Telegram",
    "role": "Роль", "version": "Версия",
}


def _message(err: dict[str, Any]) -> str:
    t, ctx = err.get("type", ""), err.get("ctx") or {}
    if t == "value_error":
        return str(ctx.get("error", err.get("msg", ""))).removeprefix("Value error, ")
    if t == "missing":
        return "обязательное поле"
    if t in ("greater_than_equal", "greater_than"):
        return f"должно быть не меньше {ctx.get('ge', ctx.get('gt'))}"
    if t in ("less_than_equal", "less_than"):
        return f"должно быть не больше {ctx.get('le', ctx.get('lt'))}"
    if t == "string_too_short":
        return "не может быть пустым"
    if t == "string_too_long":
        return f"не длиннее {ctx.get('max_length')} символов"
    if t == "enum":
        return "недопустимое значение"
    if t.startswith("date") or t.startswith("datetime"):
        return "неверная дата"
    if t.startswith("uuid"):
        return "неверный идентификатор"
    if t.startswith(("int", "float", "decimal")):
        return "должно быть числом"
    return err.get("msg", "неверное значение")


def humanize_errors(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    result = []
    for err in errors:
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
        field = ".".join(loc)
        text = _message(err)
        if err.get("type") != "value_error" and loc:
            label = FIELD_LABELS.get(loc[-1], loc[-1])
            text = f"{label}: {text}"
        result.append({"field": field, "message": text})
    return result
