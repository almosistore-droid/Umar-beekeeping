"""harvest and colony operations

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13 10:30:41.154971
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('hive_movements',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('from_apiary_id', sa.UUID(), nullable=False),
    sa.Column('to_apiary_id', sa.UUID(), nullable=False),
    sa.Column('movement_date', sa.Date(), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('performed_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('from_apiary_id <> to_apiary_id', name=op.f('ck_hive_movements_different_apiaries')),
    sa.ForeignKeyConstraint(['from_apiary_id'], ['apiaries.id'], name=op.f('fk_hive_movements_from_apiary_id_apiaries'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_hive_movements_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['performed_by'], ['users.id'], name=op.f('fk_hive_movements_performed_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['to_apiary_id'], ['apiaries.id'], name=op.f('fk_hive_movements_to_apiary_id_apiaries'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hive_movements'))
    )
    op.create_index('ix_hive_movements_hive', 'hive_movements', ['hive_id', 'movement_date'], unique=False)
    op.create_table('honey_harvests',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('apiary_id', sa.UUID(), nullable=False),
    sa.Column('harvest_date', sa.Date(), nullable=False),
    sa.Column('harvest_year', sa.SmallInteger(), nullable=False),
    sa.Column('harvest_number', sa.SmallInteger(), nullable=False),
    sa.Column('honey_type', sa.String(length=80), nullable=True),
    sa.Column('frames_count', sa.SmallInteger(), nullable=False),
    sa.Column('weight_kg', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('price_per_kg', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('total_value', sa.Numeric(precision=14, scale=2), sa.Computed('weight_kg * price_per_kg', persisted=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('frames_count >= 0', name=op.f('ck_honey_harvests_frames_non_negative')),
    sa.CheckConstraint('harvest_number >= 1', name=op.f('ck_honey_harvests_number_positive')),
    sa.CheckConstraint('price_per_kg IS NULL OR price_per_kg >= 0', name=op.f('ck_honey_harvests_price_non_negative')),
    sa.CheckConstraint('weight_kg > 0', name=op.f('ck_honey_harvests_weight_positive')),
    sa.ForeignKeyConstraint(['apiary_id'], ['apiaries.id'], name=op.f('fk_honey_harvests_apiary_id_apiaries'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_honey_harvests_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_honey_harvests_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_honey_harvests')),
    sa.UniqueConstraint('hive_id', 'harvest_year', 'harvest_number', name='uq_honey_harvests_hive_year_number')
    )
    op.create_index('ix_honey_harvests_date', 'honey_harvests', ['harvest_date'], unique=False)
    op.create_table('other_products',
    sa.Column('product_type', sa.Enum('WAX', 'PROPOLIS', 'BEE_BREAD', 'POLLEN', 'ROYAL_JELLY', 'QUEENS', 'COLONIES', 'PACKAGES', name='product_type'), nullable=False),
    sa.Column('collected_at', sa.Date(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit', postgresql.ENUM(name='feed_unit', create_type=False), nullable=False),
    sa.Column('hive_id', sa.UUID(), nullable=True),
    sa.Column('apiary_id', sa.UUID(), nullable=True),
    sa.Column('price_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('total_value', sa.Numeric(precision=14, scale=2), sa.Computed('quantity * price_per_unit', persisted=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('price_per_unit IS NULL OR price_per_unit >= 0', name=op.f('ck_other_products_price_non_negative')),
    sa.CheckConstraint('quantity > 0', name=op.f('ck_other_products_quantity_positive')),
    sa.ForeignKeyConstraint(['apiary_id'], ['apiaries.id'], name=op.f('fk_other_products_apiary_id_apiaries'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_other_products_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_other_products_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_other_products'))
    )
    op.create_index('ix_other_products_date', 'other_products', ['collected_at'], unique=False)
    op.create_table('winterings',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('season', sa.String(length=9), nullable=False),
    sa.Column('pre_winter_strength', postgresql.ENUM(name='family_strength', create_type=False), nullable=True),
    sa.Column('food_kg', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('frames_count', sa.SmallInteger(), nullable=True),
    sa.Column('queen_condition', sa.String(length=120), nullable=True),
    sa.Column('pre_winter_treatment', sa.String(length=255), nullable=True),
    sa.Column('winter_location', sa.String(length=255), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('spring_strength', postgresql.ENUM(name='family_strength', create_type=False), nullable=True),
    sa.Column('result', sa.Enum('STRONG', 'WEAK', 'DIED', name='wintering_result'), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(result IS NULL) = (end_date IS NULL)', name=op.f('ck_winterings_result_iff_finished')),
    sa.CheckConstraint('end_date IS NULL OR end_date >= start_date', name=op.f('ck_winterings_end_after_start')),
    sa.CheckConstraint('food_kg IS NULL OR food_kg >= 0', name=op.f('ck_winterings_food_non_negative')),
    sa.CheckConstraint('frames_count IS NULL OR frames_count >= 0', name=op.f('ck_winterings_frames_non_negative')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_winterings_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_winterings_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_winterings')),
    sa.UniqueConstraint('hive_id', 'season', name='uq_winterings_hive_season')
    )
    op.create_table('hive_merges',
    sa.Column('target_hive_id', sa.UUID(), nullable=False),
    sa.Column('merge_date', sa.Date(), nullable=False),
    sa.Column('kept_queen_id', sa.UUID(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_hive_merges_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['kept_queen_id'], ['queens.id'], name=op.f('fk_hive_merges_kept_queen_id_queens'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['target_hive_id'], ['hives.id'], name=op.f('fk_hive_merges_target_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hive_merges'))
    )
    op.create_table('hive_splits',
    sa.Column('source_hive_id', sa.UUID(), nullable=False),
    sa.Column('new_hive_id', sa.UUID(), nullable=False),
    sa.Column('split_date', sa.Date(), nullable=False),
    sa.Column('queen_id', sa.UUID(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('source_hive_id <> new_hive_id', name=op.f('ck_hive_splits_different_hives')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_hive_splits_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['new_hive_id'], ['hives.id'], name=op.f('fk_hive_splits_new_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['queen_id'], ['queens.id'], name=op.f('fk_hive_splits_queen_id_queens'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_hive_id'], ['hives.id'], name=op.f('fk_hive_splits_source_hive_id_hives'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hive_splits'))
    )
    op.create_table('swarms',
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.Column('swarm_date', sa.Date(), nullable=False),
    sa.Column('swarm_count', sa.SmallInteger(), nullable=False),
    sa.Column('captured', sa.Boolean(), nullable=False),
    sa.Column('new_hive_id', sa.UUID(), nullable=True),
    sa.Column('new_queen_id', sa.UUID(), nullable=True),
    sa.Column('actions', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('new_hive_id IS NULL OR captured', name=op.f('ck_swarms_settled_only_if_captured')),
    sa.CheckConstraint('swarm_count >= 1', name=op.f('ck_swarms_count_positive')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_swarms_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_swarms_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['new_hive_id'], ['hives.id'], name=op.f('fk_swarms_new_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['new_queen_id'], ['queens.id'], name=op.f('fk_swarms_new_queen_id_queens'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_swarms'))
    )
    op.create_table('hive_merge_sources',
    sa.Column('merge_id', sa.UUID(), nullable=False),
    sa.Column('hive_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['hive_id'], ['hives.id'], name=op.f('fk_hive_merge_sources_hive_id_hives'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['merge_id'], ['hive_merges.id'], name=op.f('fk_hive_merge_sources_merge_id_hive_merges'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('merge_id', 'hive_id', name=op.f('pk_hive_merge_sources'))
    )


def downgrade() -> None:
    op.drop_table('hive_merge_sources')
    op.drop_table('swarms')
    op.drop_table('hive_splits')
    op.drop_table('hive_merges')
    op.drop_table('winterings')
    op.drop_index('ix_other_products_date', table_name='other_products')
    op.drop_table('other_products')
    op.drop_index('ix_honey_harvests_date', table_name='honey_harvests')
    op.drop_table('honey_harvests')
    op.drop_index('ix_hive_movements_hive', table_name='hive_movements')
    op.drop_table('hive_movements')
    bind = op.get_bind()
    for enum_name in ("wintering_result", "product_type"):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
