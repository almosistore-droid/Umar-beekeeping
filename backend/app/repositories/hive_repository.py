import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    ARCHIVED_HIVE_STATUSES,
    REMOVED_QUEEN_STATUSES,
    Apiary,
    AuditLog,
    BeeFamily,
    FamilyStrength,
    Hive,
    HiveStatus,
    Queen,
    QueenAssignment,
    QueenStatus,
)


def _natural_order(column):
    # "2" before "10": pad numeric-looking numbers for sorting
    return func.lpad(column, 20, "0")


def list_hives(
    db: Session,
    *,
    apiary_id: uuid.UUID | None = None,
    statuses: Sequence[HiveStatus] | None = None,
    strengths: Sequence[FamilyStrength] | None = None,
    needs_inspection: bool = False,
    q: str | None = None,
    include_archived: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[Hive], int]:
    stmt: Select = select(Hive).join(Apiary, Hive.apiary_id == Apiary.id)
    if apiary_id:
        stmt = stmt.where(Hive.apiary_id == apiary_id)
    if statuses:
        stmt = stmt.where(Hive.status.in_(statuses))
    elif not include_archived:
        stmt = stmt.where(Hive.status.not_in(ARCHIVED_HIVE_STATUSES))
    if needs_inspection:
        from datetime import datetime, timezone
        stmt = stmt.where(
            Hive.current_family_id.is_not(None),
            (Hive.next_inspection_at <= datetime.now(timezone.utc))
            | (Hive.next_inspection_at.is_(None) & Hive.last_inspection_at.is_(None)),
        )
    if strengths:
        strong_families = select(BeeFamily.id).where(BeeFamily.strength.in_(strengths))
        stmt = stmt.where(Hive.current_family_id.in_(strong_families))
    if q:
        term = q.strip().lstrip("№#").strip()
        like = f"%{term}%"
        queen_match = select(Queen.current_hive_id).where(Queen.queen_code.ilike(like))
        conditions = [Hive.hive_number.ilike(like), Hive.id.in_(queen_match)]
        try:
            conditions.append(Hive.id == uuid.UUID(term))
        except ValueError:
            pass
        stmt = stmt.where(or_(*conditions))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Apiary.name, _natural_order(Hive.hive_number)).limit(limit).offset(offset)
    ).unique().all()
    return list(rows), total


def find_active_hive_by_number(
    db: Session, apiary_id: uuid.UUID, number: str, exclude_id: uuid.UUID | None = None
) -> Hive | None:
    stmt = select(Hive).where(
        Hive.apiary_id == apiary_id,
        func.lower(Hive.hive_number) == number.lower(),
        Hive.status.not_in(ARCHIVED_HIVE_STATUSES),
    )
    if exclude_id:
        stmt = stmt.where(Hive.id != exclude_id)
    return db.scalars(stmt).unique().first()


def list_families(db: Session, hive_id: uuid.UUID) -> list[BeeFamily]:
    return list(
        db.scalars(
            select(BeeFamily)
            .where(BeeFamily.hive_id == hive_id)
            .order_by(BeeFamily.start_date.desc(), BeeFamily.created_at.desc())
        )
    )


def list_hive_queen_assignments(db: Session, hive_id: uuid.UUID) -> list[QueenAssignment]:
    return list(
        db.scalars(
            select(QueenAssignment)
            .where(QueenAssignment.hive_id == hive_id)
            .order_by(QueenAssignment.installed_at.desc(), QueenAssignment.created_at.desc())
        ).unique()
    )


def list_queen_assignments(db: Session, queen_id: uuid.UUID) -> list[QueenAssignment]:
    return list(
        db.scalars(
            select(QueenAssignment)
            .where(QueenAssignment.queen_id == queen_id)
            .order_by(QueenAssignment.installed_at.desc(), QueenAssignment.created_at.desc())
        ).unique()
    )


def open_assignment(db: Session, queen_id: uuid.UUID) -> QueenAssignment | None:
    return db.scalars(
        select(QueenAssignment).where(
            QueenAssignment.queen_id == queen_id, QueenAssignment.removed_at.is_(None)
        )
    ).unique().first()


def hive_history(db: Session, hive_id: uuid.UUID, limit: int = 200) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(or_(AuditLog.hive_id == hive_id, AuditLog.entity_id == hive_id))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).unique()
    )


def list_queens(
    db: Session,
    *,
    statuses: Sequence[QueenStatus] | None = None,
    q: str | None = None,
    in_hive: bool | None = None,
    include_removed: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[Queen], int]:
    stmt = select(Queen)
    if statuses:
        stmt = stmt.where(Queen.status.in_(statuses))
    elif not include_removed:
        stmt = stmt.where(Queen.status.not_in(REMOVED_QUEEN_STATUSES))
    if in_hive is True:
        stmt = stmt.where(Queen.current_hive_id.is_not(None))
    elif in_hive is False:
        stmt = stmt.where(Queen.current_hive_id.is_(None))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Queen.queen_code.ilike(like), Queen.breed.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Queen.queen_code).limit(limit).offset(offset)).all()
    return list(rows), total


def hives_by_ids(db: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, Hive]:
    if not ids:
        return {}
    return {h.id: h for h in db.scalars(select(Hive).where(Hive.id.in_(ids))).unique()}


def apiary_hive_counts(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(Hive.apiary_id, func.count())
        .where(Hive.status.not_in(ARCHIVED_HIVE_STATUSES))
        .group_by(Hive.apiary_id)
    ).all()
    return {apiary_id: count for apiary_id, count in rows}
