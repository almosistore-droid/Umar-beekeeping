"""health records

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13 10:09:45.326379
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('diseases',
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('is_quarantine', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_diseases')),
    sa.UniqueConstraint('code', name=op.f('uq_diseases_code'))
    )
    op.create_table('feedings',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('fed_at', sa.Date(), nullable=False),
    sa.Column('feed_type', sa.Enum('SUGAR_SYRUP', 'CANDY', 'HONEY', 'PROTEIN', 'POLLEN_SUBSTITUTE', 'MEDICATED', 'OTHER', name='feed_type'), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit', sa.Enum('KG', 'G', 'L', 'ML', 'PCS', name='feed_unit'), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('next_feeding_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('next_feeding_date IS NULL OR next_feeding_date >= fed_at', name=op.f('ck_feedings_next_after_date')),
    sa.CheckConstraint('quantity > 0', name=op.f('ck_feedings_quantity_positive')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_feedings_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_feedings_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feedings'))
    )
    op.create_index('ix_feedings_hive_date', 'feedings', ['hive_id', 'fed_at'], unique=False)
    op.create_table('hive_diseases',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('disease_id', sa.UUID(), nullable=False),
    sa.Column('detected_at', sa.Date(), nullable=False),
    sa.Column('severity', sa.Enum('LIGHT', 'MODERATE', 'SEVERE', name='disease_severity'), nullable=False),
    sa.Column('symptoms', sa.Text(), nullable=True),
    sa.Column('diagnosis', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('SUSPECTED', 'CONFIRMED', 'TREATING', 'RESOLVED', name='disease_case_status'), nullable=False),
    sa.Column('resolved_at', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(status = 'RESOLVED') = (resolved_at IS NOT NULL)", name=op.f('ck_hive_diseases_resolved_date_iff_resolved')),
    sa.CheckConstraint('resolved_at IS NULL OR resolved_at >= detected_at', name=op.f('ck_hive_diseases_resolved_after_detected')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_hive_diseases_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], name=op.f('fk_hive_diseases_disease_id_diseases'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_hive_diseases_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hive_diseases'))
    )
    op.create_index('ix_hive_diseases_hive_status', 'hive_diseases', ['hive_id', 'status'], unique=False)
    op.create_table('hive_inspections',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('inspected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('strength', postgresql.ENUM(name='family_strength', create_type=False), nullable=False),
    sa.Column('frames_total', sa.SmallInteger(), nullable=False),
    sa.Column('brood_frames', sa.SmallInteger(), nullable=False),
    sa.Column('honey_frames', sa.SmallInteger(), nullable=False),
    sa.Column('pollen_frames', sa.SmallInteger(), nullable=False),
    sa.Column('queen_present', sa.Boolean(), nullable=True),
    sa.Column('queen_condition', sa.Enum('GOOD', 'NORMAL', 'POOR', 'NOT_SEEN', name='queen_condition'), nullable=True),
    sa.Column('egg_laying', sa.Boolean(), nullable=True),
    sa.Column('queen_cells', sa.SmallInteger(), nullable=False),
    sa.Column('swarming_signs', sa.Boolean(), nullable=False),
    sa.Column('food_level', sa.Enum('CRITICAL', 'LOW', 'NORMAL', 'ABUNDANT', name='food_level'), nullable=True),
    sa.Column('aggressiveness', sa.SmallInteger(), nullable=True),
    sa.Column('health_status', sa.Enum('HEALTHY', 'SUSPICIOUS', 'SICK', name='inspection_health'), nullable=False),
    sa.Column('next_inspection_at', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('aggressiveness IS NULL OR aggressiveness BETWEEN 1 AND 5', name=op.f('ck_hive_inspections_aggressiveness_1_5')),
    sa.CheckConstraint('brood_frames + honey_frames + pollen_frames <= frames_total', name=op.f('ck_hive_inspections_frames_sum')),
    sa.CheckConstraint('brood_frames >= 0 AND honey_frames >= 0 AND pollen_frames >= 0', name=op.f('ck_hive_inspections_frames_non_negative')),
    sa.CheckConstraint('frames_total BETWEEN 0 AND 60', name=op.f('ck_hive_inspections_frames_total_range')),
    sa.CheckConstraint('queen_cells >= 0', name=op.f('ck_hive_inspections_queen_cells_non_negative')),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_hive_inspections_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_hive_inspections_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hive_inspections'))
    )
    op.create_index('ix_hive_inspections_hive_time', 'hive_inspections', ['hive_id', 'inspected_at'], unique=False)
    op.create_table('tasks',
    sa.Column('hive_id', sa.UUID(), nullable=True),
    sa.Column('kind', sa.Enum('INSPECTION', 'TREATMENT', 'FEEDING', 'OTHER', name='task_kind'), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'DONE', 'CANCELLED', name='task_status'), nullable=False),
    sa.Column('source_type', sa.String(length=40), nullable=True),
    sa.Column('source_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['completed_by'], ['users.id'], name=op.f('fk_tasks_completed_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_tasks_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_tasks_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tasks'))
    )
    op.create_index(op.f('ix_tasks_hive_id'), 'tasks', ['hive_id'], unique=False)
    op.create_index('ix_tasks_status_due', 'tasks', ['status', 'due_date'], unique=False)
    op.create_table('treatments',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('disease_id', sa.UUID(), nullable=True),
    sa.Column('hive_disease_id', sa.UUID(), nullable=True),
    sa.Column('treated_at', sa.Date(), nullable=False),
    sa.Column('medication', sa.String(length=120), nullable=False),
    sa.Column('dosage', sa.String(length=120), nullable=True),
    sa.Column('method', sa.String(length=120), nullable=True),
    sa.Column('performed_by', sa.UUID(), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('next_treatment_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('next_treatment_date IS NULL OR next_treatment_date >= treated_at', name=op.f('ck_treatments_next_after_date')),
    sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], name=op.f('fk_treatments_disease_id_diseases'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['hive_disease_id'], ['hive_diseases.id'], name=op.f('fk_treatments_hive_disease_id_hive_diseases'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_treatments_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['performed_by'], ['users.id'], name=op.f('fk_treatments_performed_by_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_treatments'))
    )
    op.create_index('ix_treatments_hive_date', 'treatments', ['hive_id', 'treated_at'], unique=False)

    # Disease catalog required by the spec (section 11)
    diseases = sa.table(
        "diseases",
        sa.column("id", sa.UUID()), sa.column("code", sa.String()), sa.column("name", sa.String()),
        sa.column("is_quarantine", sa.Boolean()), sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.SmallInteger()),
    )
    import uuid as _uuid
    rows = [
        ("VARROOSIS", "Варроатоз", False), ("NOSEMOSIS", "Нозематоз", False),
        ("AFB", "Американский гнилец", True), ("EFB", "Европейский гнилец", False),
        ("CHALKBROOD", "Аскосфероз (известковый расплод)", False), ("VIRAL", "Вирусные болезни", False),
        ("WAX_MOTH", "Восковая моль", False), ("OTHER", "Другое", False),
    ]
    op.bulk_insert(diseases, [
        {"id": _uuid.uuid4(), "code": c, "name": n, "is_quarantine": q, "is_active": True, "sort_order": (i + 1) * 10}
        for i, (c, n, q) in enumerate(rows)
    ])

def downgrade() -> None:
    op.drop_index('ix_treatments_hive_date', table_name='treatments')
    op.drop_table('treatments')
    op.drop_index('ix_tasks_status_due', table_name='tasks')
    op.drop_index(op.f('ix_tasks_hive_id'), table_name='tasks')
    op.drop_table('tasks')
    op.drop_index('ix_hive_inspections_hive_time', table_name='hive_inspections')
    op.drop_table('hive_inspections')
    op.drop_index('ix_hive_diseases_hive_status', table_name='hive_diseases')
    op.drop_table('hive_diseases')
    op.drop_index('ix_feedings_hive_date', table_name='feedings')
    op.drop_table('feedings')
    op.drop_table('diseases')
    bind = op.get_bind()
    for enum_name in ("task_status", "task_kind", "feed_unit", "feed_type", "disease_case_status",
                      "disease_severity", "inspection_health", "food_level", "queen_condition"):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
