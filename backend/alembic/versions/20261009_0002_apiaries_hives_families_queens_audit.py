"""apiaries hives families queens audit

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09 16:40:30.295925
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('apiaries',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('latitude', sa.Numeric(precision=9, scale=6, asdecimal=False), nullable=True),
    sa.Column('longitude', sa.Numeric(precision=9, scale=6, asdecimal=False), nullable=True),
    sa.Column('owner_id', sa.UUID(), nullable=True),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('latitude IS NULL OR latitude BETWEEN -90 AND 90', name=op.f('ck_apiaries_latitude_range')),
    sa.CheckConstraint('longitude IS NULL OR longitude BETWEEN -180 AND 180', name=op.f('ck_apiaries_longitude_range')),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_apiaries_owner_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_apiaries'))
    )
    op.create_index(op.f('ix_apiaries_owner_id'), 'apiaries', ['owner_id'], unique=False)
    op.create_table('audit_logs',
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('entity_type', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=False),
    sa.Column('hive_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=40), nullable=False),
    sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_hive_id'), 'audit_logs', ['hive_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_table('hives',
    sa.Column('apiary_id', sa.UUID(), nullable=False),
    sa.Column('hive_number', sa.String(length=20), nullable=False),
    sa.Column('hive_type', sa.Enum('DADANT', 'LANGSTROTH', 'RUTA', 'ALPINE', 'HORIZONTAL', 'MULTI_BODY', 'NUCLEUS', 'OTHER', name='hive_type'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'WEAK', 'STRONG', 'SICK', 'QUEENLESS', 'EMPTY', 'QUARANTINE', 'MERGED', 'SPLIT', 'SOLD', 'LOST', name='hive_status'), nullable=False),
    sa.Column('installation_date', sa.Date(), nullable=True),
    sa.Column('colonization_date', sa.Date(), nullable=True),
    sa.Column('current_family_id', sa.UUID(), nullable=True),
    sa.Column('current_queen_id', sa.UUID(), nullable=True),
    sa.Column('last_inspection_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_inspection_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('version >= 1', name=op.f('ck_hives_version_positive')),
    sa.ForeignKeyConstraint(['apiary_id'], ['apiaries.id'], name=op.f('fk_hives_apiary_id_apiaries'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hives'))
    )
    op.create_index(op.f('ix_hives_apiary_id'), 'hives', ['apiary_id'], unique=False)
    op.create_index(op.f('ix_hives_status'), 'hives', ['status'], unique=False)
    op.create_index('uq_hives_apiary_number_active', 'hives', ['apiary_id', 'hive_number'], unique=True, postgresql_where=sa.text("status NOT IN ('MERGED', 'SOLD', 'LOST')"))
    op.create_table('bee_families',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('strength', sa.Enum('VERY_WEAK', 'WEAK', 'MEDIUM', 'STRONG', 'VERY_STRONG', name='family_strength'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'REPLACED', 'MERGED', 'SOLD', 'DEAD', 'ABSCONDED', name='family_status'), nullable=False),
    sa.Column('origin', sa.Enum('PURCHASED', 'PACKAGE', 'NUCLEUS', 'SWARM', 'SPLIT', 'MERGE', 'OWN', 'OTHER', name='family_origin'), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('end_reason', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('end_date IS NULL OR end_date >= start_date', name=op.f('ck_bee_families_dates_order')),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_bee_families_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bee_families'))
    )
    op.create_index(op.f('ix_bee_families_hive_id'), 'bee_families', ['hive_id'], unique=False)
    op.create_index('uq_bee_families_active_per_hive', 'bee_families', ['hive_id'], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table('queens',
    sa.Column('queen_code', sa.String(length=40), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('birth_year', sa.SmallInteger(), nullable=True),
    sa.Column('breed', sa.String(length=80), nullable=True),
    sa.Column('origin', sa.Enum('OWN_BRED', 'PURCHASED', 'SWARM', 'SUPERSEDURE', 'EMERGENCY', 'UNKNOWN', name='queen_origin'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'GOOD', 'OBSERVATION', 'WEAK', 'LOST', 'REPLACED', 'DEAD', 'SOLD', name='queen_status'), nullable=False),
    sa.Column('current_hive_id', sa.UUID(), nullable=True),
    sa.Column('installed_at', sa.Date(), nullable=True),
    sa.Column('removed_at', sa.Date(), nullable=True),
    sa.Column('removal_reason', sa.String(length=255), nullable=True),
    sa.Column('egg_laying_quality', sa.SmallInteger(), nullable=True),
    sa.Column('swarming_tendency', sa.SmallInteger(), nullable=True),
    sa.Column('temperament', sa.SmallInteger(), nullable=True),
    sa.Column('marking_color', sa.String(length=20), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('birth_date IS NULL OR birth_year IS NULL OR EXTRACT(YEAR FROM birth_date) = birth_year', name=op.f('ck_queens_birth_year_matches_date')),
    sa.CheckConstraint('birth_year IS NULL OR birth_year BETWEEN 1990 AND 2200', name=op.f('ck_queens_birth_year_range')),
    sa.CheckConstraint('egg_laying_quality IS NULL OR egg_laying_quality BETWEEN 1 AND 5', name=op.f('ck_queens_egg_laying_1_5')),
    sa.CheckConstraint('removed_at IS NULL OR installed_at IS NULL OR removed_at >= installed_at', name=op.f('ck_queens_removal_after_install')),
    sa.CheckConstraint('swarming_tendency IS NULL OR swarming_tendency BETWEEN 1 AND 5', name=op.f('ck_queens_swarming_1_5')),
    sa.CheckConstraint('temperament IS NULL OR temperament BETWEEN 1 AND 5', name=op.f('ck_queens_temperament_1_5')),
    sa.ForeignKeyConstraint(['current_hive_id'], ['hives.id'], name=op.f('fk_queens_current_hive_id_hives'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_queens')),
    sa.UniqueConstraint('queen_code', name=op.f('uq_queens_queen_code'))
    )
    op.create_index(op.f('ix_queens_status'), 'queens', ['status'], unique=False)
    op.create_index('uq_queens_current_hive', 'queens', ['current_hive_id'], unique=True, postgresql_where=sa.text('current_hive_id IS NOT NULL'))
    op.create_table('queen_assignments',
    sa.Column('queen_id', sa.UUID(), nullable=False),
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('installed_at', sa.Date(), nullable=False),
    sa.Column('removed_at', sa.Date(), nullable=True),
    sa.Column('removal_reason', sa.String(length=255), nullable=True),
    sa.Column('installed_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('removed_at IS NULL OR removed_at >= installed_at', name=op.f('ck_queen_assignments_dates_order')),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_queen_assignments_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['installed_by'], ['users.id'], name=op.f('fk_queen_assignments_installed_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['queen_id'], ['queens.id'], name=op.f('fk_queen_assignments_queen_id_queens'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_queen_assignments'))
    )
    op.create_index(op.f('ix_queen_assignments_hive_id'), 'queen_assignments', ['hive_id'], unique=False)
    op.create_index(op.f('ix_queen_assignments_queen_id'), 'queen_assignments', ['queen_id'], unique=False)
    op.create_index('uq_queen_assignments_open_per_queen', 'queen_assignments', ['queen_id'], unique=True, postgresql_where=sa.text('removed_at IS NULL'))

    # hives <-> bee_families / queens reference each other, so these FKs are added last
    op.create_foreign_key(op.f('fk_hives_current_family_id_bee_families'), 'hives', 'bee_families',
                          ['current_family_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('fk_hives_current_queen_id_queens'), 'hives', 'queens',
                          ['current_queen_id'], ['id'], ondelete='SET NULL')

def downgrade() -> None:
    op.drop_constraint(op.f('fk_hives_current_queen_id_queens'), 'hives', type_='foreignkey')
    op.drop_constraint(op.f('fk_hives_current_family_id_bee_families'), 'hives', type_='foreignkey')
    op.drop_index('uq_queen_assignments_open_per_queen', table_name='queen_assignments', postgresql_where=sa.text('removed_at IS NULL'))
    op.drop_index(op.f('ix_queen_assignments_queen_id'), table_name='queen_assignments')
    op.drop_index(op.f('ix_queen_assignments_hive_id'), table_name='queen_assignments')
    op.drop_table('queen_assignments')
    op.drop_index('uq_queens_current_hive', table_name='queens', postgresql_where=sa.text('current_hive_id IS NOT NULL'))
    op.drop_index(op.f('ix_queens_status'), table_name='queens')
    op.drop_table('queens')
    op.drop_index('uq_bee_families_active_per_hive', table_name='bee_families', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index(op.f('ix_bee_families_hive_id'), table_name='bee_families')
    op.drop_table('bee_families')
    op.drop_index('uq_hives_apiary_number_active', table_name='hives', postgresql_where=sa.text("status NOT IN ('MERGED', 'SOLD', 'LOST')"))
    op.drop_index(op.f('ix_hives_status'), table_name='hives')
    op.drop_index(op.f('ix_hives_apiary_id'), table_name='hives')
    op.drop_table('hives')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_hive_id'), table_name='audit_logs')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_apiaries_owner_id'), table_name='apiaries')
    op.drop_table('apiaries')
    bind = op.get_bind()
    for enum_name in ('queen_origin', 'queen_status', 'family_origin', 'family_status',
                      'family_strength', 'hive_status', 'hive_type'):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
