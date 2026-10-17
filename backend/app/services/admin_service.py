"""Admin panel: invitations (role on first login), system overview, activity log. ADMIN only."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ARCHIVED_HIVE_STATUSES,
    Apiary,
    AuditLog,
    BeeFamily,
    Customer,
    Expense,
    Feeding,
    FamilyStatus,
    Hive,
    HiveDisease,
    HoneyHarvest,
    Inspection,
    InviteStatus,
    Order,
    OtherProduct,
    Queen,
    Sale,
    Task,
    Treatment,
    User,
    UserInvite,
    UserRole,
)
from app.models.enums import DiseaseCaseStatus, OrderStatus, TaskStatus
from app.models.operations import HiveMerge, HiveMovement, HiveSplit, Swarm
from app.schemas.admin import (
    AuditPage,
    AuditRow,
    CountRow,
    InviteCreate,
    InviteOut,
    InviteResult,
    OverviewOut,
    SystemInfo,
)
from app.schemas.auth import UserOut
from app.services import audit_service as audit
from app.services import qr_service
from app.utils.errors import ConflictError, NotFoundError

INVITE_DAYS = 30
ROLE_NAMES = {UserRole.ADMIN: "администратор", UserRole.BEEKEEPER: "пчеловод",
              UserRole.ASSISTANT: "помощник", UserRole.VIEWER: "наблюдатель"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- invitations ----------

def invite_out(i: UserInvite) -> InviteOut:
    return InviteOut(
        id=i.id, telegram_id=i.telegram_id, username=i.username, role=i.role, note=i.note, status=i.status,
        expired=i.status == InviteStatus.PENDING and i.expires_at < _now(), expires_at=i.expires_at,
        created_at=i.created_at, created_by_name=i.author.display_name if i.author else None,
        used_by_name=i.joined.display_name if i.joined else None, used_at=i.used_at,
    )


def share_text(role: UserRole) -> str:
    """Message the admin forwards to the person: where to open the app."""
    s = get_settings()
    bot = s.telegram_bot_username.strip().lstrip("@")
    link = (f"https://t.me/{bot}/{s.telegram_webapp_short_name}" if bot and s.telegram_webapp_short_name
            else f"https://t.me/{bot}" if bot else None)
    where = f"Откройте бота: {link} и нажмите кнопку «Пасека»." if link else "Откройте нашего бота и нажмите кнопку «Пасека»."
    return f"Вас добавили в учёт пасеки {s.brand_name} ({ROLE_NAMES[role]}). {where}"


def _find_user(db: Session, data: InviteCreate) -> User | None:
    if data.telegram_id is not None:
        user = db.scalar(select(User).where(User.telegram_id == data.telegram_id))
        if user:
            return user
    if data.username:
        return db.scalar(select(User).where(func.lower(User.username) == data.username))
    return None


def create_invite(db: Session, data: InviteCreate, admin: User) -> InviteResult:
    user = _find_user(db, data)
    if user is not None:
        if user.id == admin.id:
            raise ConflictError("Это вы. Свою роль изменить нельзя")
        before = audit.snapshot(user, ["role", "is_active"])
        user.role, user.is_active = data.role, True
        old, new = audit.diff(before, audit.snapshot(user, ["role", "is_active"]))
        if new:
            audit.record(db, user=admin, entity_type="user", entity_id=user.id, action="updated", old=old, new=new,
                         comment="Через «Добавить пользователя»")
        db.commit()
        db.refresh(user)
        return InviteResult(kind="updated", user=UserOut.model_validate(user))

    _expire_old(db)
    clash = db.scalar(select(UserInvite).where(UserInvite.status == InviteStatus.PENDING, or_(
        (UserInvite.telegram_id == data.telegram_id) if data.telegram_id is not None else False,
        (UserInvite.username == data.username) if data.username else False)))
    if clash:
        raise ConflictError("Для этого человека уже есть приглашение. Отзовите его, чтобы создать новое")
    invite = UserInvite(telegram_id=data.telegram_id, username=data.username, role=data.role, note=data.note,
                        status=InviteStatus.PENDING, expires_at=_now() + timedelta(days=INVITE_DAYS), created_by=admin.id)
    db.add(invite)
    db.flush()
    audit.record(db, user=admin, entity_type="user_invite", entity_id=invite.id, action="invited",
                 new={"telegram_id": data.telegram_id, "username": data.username, "role": data.role.value, "note": data.note})
    db.commit()
    db.refresh(invite)
    return InviteResult(kind="invited", invite=invite_out(invite), share_text=share_text(data.role))


def _expire_old(db: Session) -> None:
    """Expired invitations stop blocking new ones for the same person (they are kept as REVOKED)."""
    for i in db.scalars(select(UserInvite).where(UserInvite.status == InviteStatus.PENDING,
                                                 UserInvite.expires_at < _now())):
        i.status = InviteStatus.REVOKED
    db.flush()


def list_invites(db: Session) -> list[InviteOut]:
    rows = db.scalars(select(UserInvite).order_by(
        (UserInvite.status != InviteStatus.PENDING), UserInvite.created_at.desc()).limit(100)).unique()
    return [invite_out(i) for i in rows]


def revoke_invite(db: Session, invite_id: uuid.UUID, admin: User) -> InviteOut:
    invite = db.get(UserInvite, invite_id)
    if invite is None:
        raise NotFoundError("Приглашение не найдено")
    if invite.status != InviteStatus.PENDING:
        raise ConflictError("Приглашение уже использовано или отозвано")
    invite.status = InviteStatus.REVOKED
    audit.record(db, user=admin, entity_type="user_invite", entity_id=invite.id, action="invite_revoked",
                 old={"status": "PENDING"}, new={"status": "REVOKED"})
    db.commit()
    db.refresh(invite)
    return invite_out(invite)


def claim_invite(db: Session, user: User) -> UserInvite | None:
    """Called on a user's first login (before commit): apply a pending invitation, ID first, then username."""
    base = select(UserInvite).where(UserInvite.status == InviteStatus.PENDING, UserInvite.expires_at >= _now())
    invite = db.scalar(base.where(UserInvite.telegram_id == user.telegram_id))
    if invite is None and user.username:
        invite = db.scalar(base.where(UserInvite.username == user.username.lower(), UserInvite.telegram_id.is_(None)))
    if invite is None:
        return None
    invite.status, invite.used_by, invite.used_at = InviteStatus.USED, user.id, _now()
    return invite


# ---------- overview ----------

def _count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def _num(v) -> str:
    return f"{v:,.0f}".replace(",", " ") if float(v) == int(v) else f"{v:,.1f}".replace(",", " ").replace(".", ",")


def overview(db: Session) -> OverviewOut:
    s = get_settings()
    try:
        size = db.scalar(text("SELECT pg_database_size(current_database())"))
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        db_ok = True
    except Exception:  # noqa: BLE001 — shown as «нет связи», never breaks the page
        db.rollback()
        size, revision, db_ok = None, None, False

    roles = dict(db.execute(select(User.role, func.count()).where(User.is_active).group_by(User.role)).all())
    users = {r.value: roles.get(r, 0) for r in UserRole}
    users["blocked"] = _count(db, User, User.is_active.is_(False))
    users["pending_invites"] = _count(db, UserInvite, UserInvite.status == InviteStatus.PENDING, UserInvite.expires_at >= _now())
    users["seen_7_days"] = _count(db, User, User.last_seen_at >= _now() - timedelta(days=7))

    month_ago = _now() - timedelta(days=30)
    honey = db.scalar(select(func.coalesce(func.sum(HoneyHarvest.weight_kg), 0))) or 0
    rows = [
        ("Пасека", "Пасеки (в работе / в архиве)", f"{_count(db, Apiary, Apiary.is_archived.is_(False))} / {_count(db, Apiary, Apiary.is_archived.is_(True))}"),
        ("Пасека", "Ульи (на пасеках / в архиве)", f"{_count(db, Hive, Hive.status.not_in(ARCHIVED_HIVE_STATUSES))} / {_count(db, Hive, Hive.status.in_(ARCHIVED_HIVE_STATUSES))}"),
        ("Пасека", "Пчелиные семьи (живые / всего в истории)", f"{_count(db, BeeFamily, BeeFamily.status == FamilyStatus.ACTIVE)} / {_count(db, BeeFamily)}"),
        ("Пасека", "Матки (в ульях / всего)", f"{_count(db, Hive, Hive.current_queen_id.is_not(None), Hive.status.not_in(ARCHIVED_HIVE_STATUSES))} / {_count(db, Queen)}"),
        ("Здоровье", "Осмотры (за 30 дней / всего)", f"{_count(db, Inspection, Inspection.inspected_at >= month_ago)} / {_count(db, Inspection)}"),
        ("Здоровье", "Болезни (открыты / всего)", f"{_count(db, HiveDisease, HiveDisease.status != DiseaseCaseStatus.RESOLVED)} / {_count(db, HiveDisease)}"),
        ("Здоровье", "Обработки", _num(_count(db, Treatment))),
        ("Здоровье", "Подкормки", _num(_count(db, Feeding))),
        ("Здоровье", "Напоминания (открыты / всего)", f"{_count(db, Task, Task.status == TaskStatus.OPEN)} / {_count(db, Task)}"),
        ("Мёд и операции", "Откачки мёда", f"{_count(db, HoneyHarvest)} ({_num(honey)} кг)"),
        ("Мёд и операции", "Другая продукция", _num(_count(db, OtherProduct))),
        ("Мёд и операции", "Роения / отводки / объединения", f"{_count(db, Swarm)} / {_count(db, HiveSplit)} / {_count(db, HiveMerge)}"),
        ("Мёд и операции", "Перемещения ульев", _num(_count(db, HiveMovement))),
        ("CRM", "Клиенты", _num(_count(db, Customer))),
        ("CRM", "Продажи (действующие / отменённые)", f"{_count(db, Sale, Sale.cancelled_at.is_(None))} / {_count(db, Sale, Sale.cancelled_at.is_not(None))}"),
        ("CRM", "Заказы (открыты / всего)", f"{_count(db, Order, Order.status.in_([OrderStatus.NEW, OrderStatus.READY]))} / {_count(db, Order)}"),
        ("CRM", "Расходы", _num(_count(db, Expense, Expense.cancelled_at.is_(None)))),
        ("Система", "Записей в журнале действий", _num(_count(db, AuditLog))),
    ]
    bot = s.telegram_bot_username.strip().lstrip("@") or None
    return OverviewOut(
        system=SystemInfo(
            environment=s.environment, timezone=s.timezone, currency=s.currency, server_time=_now(),
            bot_configured=bool(s.telegram_bot_token) and not s.telegram_bot_token.endswith("local-test-token"),
            bot_username=bot, deep_links_ready=qr_service.deep_link("x") is not None, database_ok=db_ok,
            database_size_mb=round(size / 1024 / 1024, 1) if size else None, migration=revision,
        ),
        users=users,
        counts=[CountRow(section=a, label=b, value=c) for a, b, c in rows],
    )


# ---------- activity log ----------

def audit_log(db: Session, *, user_id: uuid.UUID | None, entity_type: str | None, offset: int,
              limit: int) -> AuditPage:
    stmt = (select(AuditLog, Hive.hive_number).outerjoin(Hive, Hive.id == AuditLog.hive_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc()))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    rows = db.execute(stmt.offset(offset).limit(limit + 1)).all()
    more = len(rows) > limit
    rows = rows[:limit]
    items = [AuditRow(
        id=e.id, created_at=e.created_at, user_id=e.user_id, user_name=e.user.display_name if e.user else None,
        entity_type=e.entity_type, entity_id=e.entity_id, hive_id=e.hive_id, hive_number=number, action=e.action,
        old_value=e.old_value, new_value=e.new_value, comment=e.comment,
    ) for e, number in rows]
    types = list(db.scalars(select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)))
    return AuditPage(items=items, next_offset=offset + limit if more else None, entity_types=types)
