"""Stage 8: Telegram reminders, one message per reminder.

`collect()` lists what is due today (Russian text + a button to open the hive or the right screen);
`dispatch()` sends each reminder once to every person it concerns and records it in notification_log
(claimed before sending, so two runs at the same time never send twice).

Who gets what: ADMIN and BEEKEEPER — everything; ASSISTANT — work at the apiary (no money);
VIEWER — nothing. Each person can turn off apiary or CRM reminders in «Ещё».
"""
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.i18n import translate
from app.models import (
    ARCHIVED_HIVE_STATUSES,
    Hive,
    HiveStatus,
    NotificationLog,
    Order,
    Task,
    User,
    UserRole,
)
from app.models.enums import FamilyStrength, OrderStatus, TaskKind, TaskStatus
from app.schemas.common import app_zone, stored_day
from app.services import crm_service, qr_service, telegram_bot
from app.utils.age import age_in_months, age_label

FIELD, CRM, STOCK = "field", "crm", "stock"
OVERDUE_AGAIN_DAYS = 3      # one more reminder when still not done after this many days
LOOKBACK_DAYS = 30          # older forgotten items are not sent (no flood on the first run)
OLD_QUEEN_MONTHS = 24
MAX_PER_RUN = 200

FIELD_ROLES = {UserRole.ADMIN, UserRole.BEEKEEPER, UserRole.ASSISTANT}
CRM_ROLES = {UserRole.ADMIN, UserRole.BEEKEEPER}
TASK_ICON = {TaskKind.TREATMENT: "💊", TaskKind.FEEDING: "🍯", TaskKind.INSPECTION: "🔍", TaskKind.OTHER: "📌"}


@dataclass(frozen=True)
class Note:
    key: str
    category: str          # FIELD | CRM | STOCK
    lines: tuple[str, ...]  # Russian, one template per line; each line is translated for the person
    button: str | None = None
    start: str | None = None  # Mini App start parameter: hive_<uuid> or go_<screen>


def _fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _money(x: Decimal) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",").removesuffix(",00")


def _hive_line(hive: Hive | None) -> str:
    if hive is None:
        return ""
    return f"Улей №{hive.hive_number} · {hive.apiary.name}" if hive.apiary else f"Улей №{hive.hive_number}"


def _hive_note(key: str, lines: list[str], hive: Hive | None, category: str = FIELD) -> Note:
    lines = tuple(x for x in lines if x)
    if hive is not None:
        return Note(key, category, lines, "Открыть улей", qr_service.payload(hive.id))
    return Note(key, category, lines, "Напоминания", "go_tasks")


def _tasks(db: Session, today: date) -> list[Note]:
    tasks = db.scalars(select(Task).where(Task.status == TaskStatus.OPEN, Task.due_date <= today,
                                          Task.due_date >= today - timedelta(days=LOOKBACK_DAYS))
                       .order_by(Task.due_date)).all()
    hives = {h.id: h for h in db.scalars(select(Hive).where(Hive.id.in_({t.hive_id for t in tasks if t.hive_id})))}
    notes = []
    for t in tasks:
        hive = hives.get(t.hive_id)
        if hive is not None and hive.status in ARCHIVED_HIVE_STATUSES:
            continue
        icon, where = TASK_ICON[t.kind], _hive_line(hive)
        if t.due_date == today:
            lines = [f"{icon} Сегодня: {t.title}", where]
        else:
            lines = [f"⏰ Просрочено: {t.title}", where, f"Срок был {_fmt(t.due_date)}"]
        notes.append(_hive_note(f"task:{t.id}:due", lines, hive))
        if (today - t.due_date).days >= OVERDUE_AGAIN_DAYS:
            lines = [f"⏰ Всё ещё не сделано: {t.title}", where, f"Срок был {_fmt(t.due_date)}"]
            notes.append(_hive_note(f"task:{t.id}:overdue", lines, hive))
    return notes


def _active_hives(db: Session) -> list[Hive]:
    return list(db.scalars(select(Hive).where(Hive.status.not_in(ARCHIVED_HIVE_STATUSES))
                           .order_by(Hive.hive_number)).unique())


def _inspections(hives: list[Hive], today: date) -> list[Note]:
    notes = []
    for h in hives:
        if h.next_inspection_at is None:
            continue
        due = stored_day(h.next_inspection_at)
        if due > today or due < today - timedelta(days=LOOKBACK_DAYS):
            continue
        last = f"Последний осмотр: {_fmt(stored_day(h.last_inspection_at))}" if h.last_inspection_at \
            else "Осмотров ещё не было"
        if due == today:
            lines = ["🔍 Сегодня осмотр", _hive_line(h), last]
        else:
            lines = ["🔍 Напоминание", f"Улей №{h.hive_number} давно не осматривался.", last]
        notes.append(_hive_note(f"inspection:{h.id}:{due.isoformat()}", lines, h))
        if (today - due).days >= OVERDUE_AGAIN_DAYS:
            lines = [f"🔍 Улей №{h.hive_number} всё ещё ждёт осмотра.", last]
            notes.append(_hive_note(f"inspection:{h.id}:{due.isoformat()}:overdue", lines, h))
    return notes


def _queens(hives: list[Hive], today: date) -> list[Note]:
    notes = []
    week = "{}-W{:02d}".format(*today.isocalendar()[:2])
    for h in hives:
        if h.status == HiveStatus.QUEENLESS:
            lines = [f"⚠️ Улей №{h.hive_number} без матки.", "Подсадите матку или объедините семью."]
            notes.append(_hive_note(f"queenless:{h.id}:{week}", lines, h))
        q = h.current_queen
        if q is None:
            continue
        months = age_in_months(q.birth_date, q.birth_year, today)
        if months is not None and months >= OLD_QUEEN_MONTHS:
            lines = [f"👑 Матке {q.queen_code} в улье №{h.hive_number} уже {age_label(q.birth_date, q.birth_year, today)}.",
                     "Пора планировать замену."]
            notes.append(_hive_note(f"queen_old:{q.id}", lines, h))
    return notes


def _wintering(hives: list[Hive], today: date) -> list[Note]:
    if (today.month == 9 and today.day >= 15) or today.month in (10, 11):
        families = [h for h in hives if h.current_family is not None]
        weak = sum(1 for h in families if h.current_family.strength in (FamilyStrength.VERY_WEAK, FamilyStrength.WEAK))
        lines = (f"❄️ Пора готовить пасеку к зимовке: семей {len(families)}, слабых {weak}.",
                 "Проверьте запас корма и утепление, слабые семьи объедините.")
        return [Note(f"wintering_prep:{today.year}", FIELD, lines, "Ульи", "go_hives")]
    if (today.month == 3 and today.day >= 20) or today.month == 4:
        lines = ("🌱 Весенняя ревизия: отметьте итоги зимовки по каждому улью (паспорт улья → Зимовка).",)
        return [Note(f"wintering_check:{today.year}", FIELD, lines, "Ульи", "go_hives")]
    return []


def _crm(db: Session, settings: Settings, today: date) -> list[Note]:
    notes = []
    week = "{}-W{:02d}".format(*today.isocalendar()[:2])
    for d in crm_service.debts(db):
        if d.customer is None or d.debt <= 0:
            continue
        lines = [f"💰 Долг клиента {d.customer.name}: {_money(d.debt)} {settings.currency}"]
        if d.customer.phone:
            lines.append(f"Телефон: {d.customer.phone}")
        notes.append(Note(f"debt:{d.customer.id}:{week}", CRM, tuple(lines), "Долги", "go_debts"))
    orders = db.scalars(select(Order).where(Order.status.in_([OrderStatus.NEW, OrderStatus.READY]),
                                            Order.due_date.is_not(None), Order.due_date <= today,
                                            Order.due_date >= today - timedelta(days=LOOKBACK_DAYS))).all()
    for o in orders:
        total = sum((i.total or Decimal(0) for i in o.items), Decimal(0))
        ready = "собран" if o.status == OrderStatus.READY else "не собран"
        if o.due_date == today:
            line = f"📦 Заказ на сегодня: {o.customer.name} — {_money(total)} {settings.currency} ({ready})"
        else:
            line = f"📦 Заказ просрочен (срок {_fmt(o.due_date)}): {o.customer.name} — {_money(total)} {settings.currency}"
        notes.append(Note(f"order:{o.id}:{o.due_date.isoformat()}", CRM, (line,), "Заказы", "go_orders"))
    return notes


def _stock(db: Session, today: date) -> list[Note]:
    """Warehouse items below their minimum: once a week while they stay low."""
    from app.services.stock_service import UNIT_LABEL, fmt, low_items
    week = "{}-W{:02d}".format(*today.isocalendar()[:2])
    return [Note(f"stock:{i.id}:{week}", STOCK,
                 (f"📦 На складе заканчивается: {i.name} — осталось {fmt(i.quantity)} {UNIT_LABEL[i.unit]}",),
                 "Склад", "go_stock")
            for i in low_items(db)]


def collect(db: Session, settings: Settings, today: date) -> list[Note]:
    hives = _active_hives(db)
    return (_tasks(db, today) + _inspections(hives, today) + _queens(hives, today) + _wintering(hives, today)
            + _stock(db, today) + _crm(db, settings, today))


def wants(user: User, note: Note) -> bool:
    if note.category == CRM:
        return user.notify_crm and user.role in CRM_ROLES
    if note.category == STOCK:  # buying is decided by the owner and the beekeeper
        return user.notify_field and user.role in CRM_ROLES
    return user.notify_field and user.role in FIELD_ROLES


def language(user: User) -> str:
    if user.language in ("ru", "tg"):
        return user.language
    return "tg" if (user.language_code or "").lower().startswith("tg") else "ru"


def render(note: Note, lang: str) -> tuple[str, tuple[str, str] | None]:
    link = qr_service.deep_link(note.start) if note.start else None
    button = (translate(note.button, lang), link) if note.button and link else None
    return "\n".join(translate(line, lang) for line in note.lines), button


Sender = Callable[[int, str, tuple[str, str] | None], None]


def dispatch(db: Session, settings: Settings, now: datetime | None = None,
             send: Sender | None = None) -> dict:
    """Send everything due and not sent yet. Outside the allowed hours nothing is sent."""
    send = send or telegram_bot.send_message
    local = (now or datetime.now(app_zone())).astimezone(app_zone())
    if not settings.notify_from_hour <= local.hour < settings.notify_to_hour:
        return {"status": "quiet", "sent": 0, "failed": 0, "left": 0}
    notes = collect(db, settings, local.date())
    users = db.scalars(select(User).where(User.is_active.is_(True), User.telegram_id.is_not(None),
                                          User.role != UserRole.VIEWER)).all()
    done = {(r.user_id, r.key) for r in db.execute(
        select(NotificationLog.user_id, NotificationLog.key).where(NotificationLog.key.in_({n.key for n in notes})))}
    sent = failed = left = 0
    for note in notes:
        for user in users:
            if (user.id, note.key) in done or not wants(user, note):
                continue
            if sent + failed >= MAX_PER_RUN:
                left += 1
                continue
            if not _claim(db, user.id, note):
                continue  # another run took it
            text, button = render(note, language(user))
            try:
                send(user.telegram_id, text, button)
                sent += 1
            except telegram_bot.TelegramBlocked as exc:
                _finish(db, user.id, note.key, error=exc.message)
                failed += 1
            except telegram_bot.TelegramUnavailable:
                _release(db, user.id, note.key)  # try again on the next run
                failed += 1
    return {"status": "ok", "sent": sent, "failed": failed, "left": left}


def _claim(db: Session, user_id: uuid.UUID, note: Note) -> bool:
    row = db.execute(insert(NotificationLog).values(id=uuid.uuid4(), user_id=user_id, key=note.key,
                                                   category=note.category, status="SENT")
                     .on_conflict_do_nothing(constraint="uq_notification_log_user_key")
                     .returning(NotificationLog.id)).first()
    db.commit()
    return row is not None


def _finish(db: Session, user_id: uuid.UUID, key: str, error: str) -> None:
    db.execute(update(NotificationLog).where(NotificationLog.user_id == user_id, NotificationLog.key == key)
               .values(status="FAILED", error=error[:300]))
    db.commit()


def _release(db: Session, user_id: uuid.UUID, key: str) -> None:
    db.execute(delete(NotificationLog).where(NotificationLog.user_id == user_id, NotificationLog.key == key))
    db.commit()


def test_lines(settings: Settings) -> tuple[str, ...]:
    return (f"🔔 Уведомления {settings.brand_name} работают.",
            "Так будут приходить напоминания об осмотрах, обработках, подкормках и других делах на пасеке.")


def send_test(user: User, settings: Settings) -> None:
    from app.utils.errors import ConflictError
    if user.telegram_id is None:
        raise ConflictError("У вас нет Telegram в профиле — уведомления приходят только в Telegram")
    try:
        text = "\n".join(translate(line, language(user)) for line in test_lines(settings))
        telegram_bot.send_message(user.telegram_id, text)
    except telegram_bot.TelegramBlocked:
        raise ConflictError("Бот не может написать вам: откройте чат с ботом и нажмите «Start»") from None
