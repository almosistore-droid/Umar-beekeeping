"""Yearly report files: PDF (reportlab, bundled DejaVu fonts), Excel (openpyxl), CSV (UTF-8 BOM, «;»)."""
import csv
import io
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import get_settings
from app.i18n import L
from app.schemas.report import YearlyReportOut
from app.services.qr_labels import _register_fonts
from app.utils.age import plural_ru
from app.utils.labels import FEED_UNIT, MONTHS, PRODUCT_TYPE

FORMATS = {
    "pdf": ("application/pdf", "pdf"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "csv": ("text/csv; charset=utf-8", "csv"),
}
INK, MUTED, RULE, HONEY = HexColor("#15120c"), HexColor("#6b6458"), HexColor("#d9d3c7"), HexColor("#c08918")


def fmt(v: Decimal | int | float | None, digits: int = 1) -> str:
    """1 234,5 — Russian number format; whole numbers without decimals."""
    if v is None:
        return "—"
    d = Decimal(v)
    s = f"{d:,.0f}" if d == d.to_integral_value() else f"{d:,.{digits}f}"
    return s.replace(",", " ").replace(".", ",")


def _ru_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d.%m.%Y")


def summary(r: YearlyReportOut) -> list[tuple[str, list[tuple[str, str]]]]:
    """The report as titled sections of (label, value) — shared by every format."""
    h, q, m, d = r.hives, r.queens, r.honey, r.diseases
    age = "—" if q.avg_age_months is None else f"{fmt(q.avg_age_months / 12, 1)} года ({fmt(q.avg_age_months)} мес.)"
    sections = [
        ("Ульи", [
            ("На начало года", fmt(h.at_start)),
            ("На конец периода", fmt(h.at_end)),
            ("Новые", fmt(h.new)), ("Потеряны", fmt(h.lost)), ("Проданы", fmt(h.sold)),
            ("Объединены (ушли в другой улей)", fmt(h.merged)), ("Разделены (отводки)", fmt(h.split)),
        ]),
        ("Матки", [
            ("В ульях на конец периода", fmt(q.in_hives)), ("Новые", fmt(q.new)), ("Заменены", fmt(q.replaced)),
            ("Средний возраст", age),
        ] + ([("Возраст неизвестен", fmt(q.age_unknown))] if q.age_unknown else [])),
        ("Мёд", [
            ("Всего собрано, кг", fmt(m.total_kg)),
            ("Ульев дали мёд", fmt(m.producing_hives)),
            ("В среднем на улей, кг", fmt(m.avg_per_hive_kg)),
            ("Лучший улей", f"№{m.best_hive.hive_number} — {fmt(m.best_hive.kg)} кг" if m.best_hive else "—"),
            ("Худший улей", f"№{m.worst_hive.hive_number} — {fmt(m.worst_hive.kg)} кг" if m.worst_hive else "—"),
            ("Стоимость мёда по ценам в записях", fmt(m.value)),
        ] + [(f"{L(PRODUCT_TYPE[p.product_type])}, {L(FEED_UNIT[p.unit])}", fmt(p.quantity)) for p in m.products]),
        ("Болезни", [
            ("Случаев выявлено", fmt(d.cases)), ("Вылечено", fmt(d.resolved)), ("Ещё не вылечено", fmt(d.open)),
            ("Обработок проведено", fmt(d.treatments)),
        ] + [(f"Препарат: {x.medication}", f"{x.count} {plural_ru(x.count, 'раз', 'раза', 'раз')}") for x in d.medications]),
        ("Финансы", _finance_rows(r)),
    ]
    # in the language of the request (X-Lang); numbers and user data stay as they are
    return [(L(section), [(L(label), L(value)) for label, value in rows]) for section, rows in sections]


def _finance_rows(r: YearlyReportOut) -> list[tuple[str, str]]:
    f = r.finance
    cur = f.currency
    rows = [("Стоимость продукции по ценам в записях", f"{fmt(f.production_value)} {cur}")]
    if not f.visible:
        return rows
    rows += [
        ("Доход (продажи)", f"{fmt(f.income)} {cur}"), ("Расход", f"{fmt(f.expenses)} {cur}"),
        ("Прибыль", f"{fmt(f.profit)} {cur}"), ("Получено денег", f"{fmt(f.received)} {cur}"),
        ("Долги клиентов сейчас", f"{fmt(f.debts_total)} {cur}"),
    ]
    rows += [(f"Доход: {x.label}", f"{fmt(x.amount)} {cur}") for x in f.income_by_category]
    rows += [(f"Расход: {x.label}", f"{fmt(x.amount)} {cur}") for x in f.expenses_by_category]
    return rows


def title(r: YearlyReportOut) -> str:
    return L(f"Годовой отчёт за {r.year}") + (L(f" (по {_ru_date(r.period_end)})") if r.is_partial else "")


# ---------- CSV ----------

class _Translated:
    """csv.writer that writes every text cell in the language of the request."""

    def __init__(self, writer):
        self._w = writer

    def writerow(self, row):
        self._w.writerow([L(c) if isinstance(c, str) else c for c in row])


def to_csv(r: YearlyReportOut) -> bytes:
    buf = io.StringIO()
    w = _Translated(csv.writer(buf, delimiter=";", lineterminator="\r\n"))
    w.writerow([title(r)])
    w.writerow([])
    w.writerow(["Раздел", "Показатель", "Значение"])
    for section, rows in summary(r):
        for label, value in rows:
            w.writerow([section, label, value])
    w.writerow([])
    w.writerow(["Мёд по месяцам", "Месяц", "кг"])
    for i, kg in enumerate(r.honey.by_month):
        w.writerow(["", MONTHS[i], fmt(kg)])
    w.writerow([])
    w.writerow(["Мёд по ульям", "Улей", "Пасека", "кг", "Откачек"])
    for x in r.honey.by_hive:
        w.writerow(["", f"№{x.hive_number}", x.apiary_name, fmt(x.kg), x.harvests])
    w.writerow([])
    w.writerow(["Болезни", "Болезнь", "Случаев", "Вылечено", "Не вылечено"])
    for x in r.diseases.by_disease:
        w.writerow(["", x.name, x.cases, x.resolved, x.open])
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: Excel detects UTF-8


# ---------- Excel ----------

_HEAD = Font(bold=True, color="FFFFFF")
_HEAD_FILL = PatternFill("solid", fgColor="15120C")


def _sheet_table(ws, headers: list[str], rows: list[list], widths: list[int]) -> None:
    ws.append([L(h) for h in headers])
    for c in ws[ws.max_row]:
        c.font, c.fill = _HEAD, _HEAD_FILL
    for row in rows:
        ws.append(row)
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "A2"


def to_xlsx(r: YearlyReportOut) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = L("Сводка")
    ws.append([title(r)])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    for section, rows in summary(r):
        ws.append([section])
        ws[f"A{ws.max_row}"].font = Font(bold=True, color="C08918", size=12)
        for label, value in rows:
            ws.append([label, value])
            ws[f"B{ws.max_row}"].alignment = Alignment(horizontal="right")
        ws.append([])
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 30

    _sheet_table(wb.create_sheet(L("Мёд по ульям")), ["Место", "Улей", "Пасека", "кг", "Откачек"],
                 [[i + 1, f"№{x.hive_number}", x.apiary_name, float(x.kg), x.harvests] for i, x in enumerate(r.honey.by_hive)],
                 [8, 12, 28, 10, 10])
    _sheet_table(wb.create_sheet(L("Мёд по месяцам")), ["Месяц", "кг"],
                 [[L(MONTHS[i]), float(kg)] for i, kg in enumerate(r.honey.by_month)], [14, 10])
    _sheet_table(wb.create_sheet(L("Болезни")), ["Болезнь", "Случаев", "Вылечено", "Не вылечено"],
                 [[L(x.name), x.cases, x.resolved, x.open] for x in r.diseases.by_disease], [32, 10, 10, 12])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------- PDF ----------

def _month_chart(by_month: list[Decimal], width: float) -> Drawing:
    """Single-series bars, one hue, 4 mm gap between bars, value above the peak only."""
    height, base = 46 * mm, 8 * mm
    d = Drawing(width, height)
    values = [float(v) for v in by_month]
    top = max(values) or 1
    slot = width / 12
    bar_w = slot * 0.6
    peak = values.index(max(values))
    d.add(Rect(0, base, width, 0.4, fillColor=RULE, strokeColor=None))
    for i, v in enumerate(values):
        x = i * slot + (slot - bar_w) / 2
        h = (v / top) * (height - base - 7 * mm)
        if v > 0:
            d.add(Rect(x, base, bar_w, max(h, 0.8), fillColor=HONEY, strokeColor=None, rx=1.2, ry=1.2))
        if i == peak and v > 0:
            d.add(String(x + bar_w / 2, base + h + 1.6 * mm, fmt(v), fontName="DejaVu-Bold", fontSize=7,
                         fillColor=INK, textAnchor="middle"))
        d.add(String(i * slot + slot / 2, base - 4.5 * mm, L(MONTHS[i])[:3], fontName="DejaVu", fontSize=6.5,
                     fillColor=MUTED, textAnchor="middle"))
    return d


def to_pdf(r: YearlyReportOut) -> bytes:
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=title(r), author=get_settings().brand_name)
    h1 = ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=18, leading=22, textColor=INK)
    sub = ParagraphStyle("sub", fontName="DejaVu", fontSize=9, leading=12, textColor=MUTED)
    h2 = ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12, leading=16, textColor=HONEY, spaceBefore=8, spaceAfter=4)
    cell = ParagraphStyle("cell", fontName="DejaVu", fontSize=9, leading=12, textColor=INK)
    table_style = TableStyle([
        ("FONT", (0, 0), (-1, -1), "DejaVu", 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])
    head_style = TableStyle([("FONT", (0, 0), (-1, 0), "DejaVu-Bold", 9), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED)])
    width = doc.width
    story = [Paragraph(title(r), h1), Paragraph(f"{get_settings().brand_name} · {L(get_settings().brand_subtitle)}", sub), Spacer(1, 4 * mm)]

    for section, rows in summary(r):
        block = [Paragraph(section, h2),
                 Table([[Paragraph(a, cell), b] for a, b in rows], colWidths=[width * 0.62, width * 0.38], style=table_style)]
        if section == "Мёд" and any(r.honey.by_month):
            block += [Spacer(1, 3 * mm), Paragraph(L("Сбор по месяцам, кг"), sub), _month_chart(r.honey.by_month, width)]
        story.append(KeepTogether(block))

    if r.queens.best_families:
        rows = [[L("Улей"), L("Пасека"), L("Матка"), L("кг")]] + [[f"№{x.hive_number}", x.apiary_name, x.queen_code or "—", fmt(x.kg)]
                                                     for x in r.queens.best_families]
        t = Table(rows, colWidths=[width * 0.18, width * 0.42, width * 0.2, width * 0.2], style=table_style)
        t.setStyle(head_style)
        t.setStyle(TableStyle([("ALIGN", (0, 0), (2, -1), "LEFT")]))
        story.append(KeepTogether([Paragraph(L("Лучшие семьи по сбору мёда"), h2), t]))
    if r.honey.by_hive:
        rows = [[L("Место"), L("Улей"), L("Пасека"), L("кг")]] + [[str(i + 1), f"№{x.hive_number}", x.apiary_name, fmt(x.kg)]
                                                     for i, x in enumerate(r.honey.by_hive)]
        t = Table(rows, colWidths=[width * 0.12, width * 0.18, width * 0.5, width * 0.2], style=table_style, repeatRows=1)
        t.setStyle(head_style)
        t.setStyle(TableStyle([("ALIGN", (0, 0), (2, -1), "LEFT")]))
        story += [Paragraph(L("Мёд по ульям"), h2), t]
    if r.diseases.by_disease:
        rows = [[L("Болезнь"), L("Случаев"), L("Вылечено"), L("Не вылечено")]] + [[L(x.name), x.cases, x.resolved, x.open]
                                                                       for x in r.diseases.by_disease]
        t = Table(rows, colWidths=[width * 0.46, width * 0.18, width * 0.18, width * 0.18], style=table_style)
        t.setStyle(head_style)
        story.append(KeepTogether([Paragraph(L("Болезни по видам"), h2), t]))

    doc.build(story)
    return buf.getvalue()


def render(r: YearlyReportOut, fmt_name: str) -> tuple[bytes, str, str]:
    """(content, media type, file name)"""
    media, ext = FORMATS[fmt_name]
    content = {"pdf": to_pdf, "xlsx": to_xlsx, "csv": to_csv}[fmt_name](r)
    return content, media, f"godovoy-otchet-{r.year}.{ext}"
