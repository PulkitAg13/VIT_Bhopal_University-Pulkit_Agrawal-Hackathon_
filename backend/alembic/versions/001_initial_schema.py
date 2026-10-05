"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-05 19:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. sources
    op.create_table(
        'sources',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('credibility_score', sa.Float(), nullable=True),
        sa.Column('credibility_label', sa.String(length=128), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=True),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('embedding_vector', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. entities
    op.create_table(
        'entities',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('canonical_name', sa.String(length=256), nullable=False),
        sa.Column('ticker', sa.String(length=16), nullable=True),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical_name')
    )
    op.create_index('ix_entities_canonical_name', 'entities', ['canonical_name'], unique=False)
    op.create_index('ix_entities_ticker', 'entities', ['ticker'], unique=False)

    # 4. document_entities
    op.create_table(
        'document_entities',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('document_id', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. event_clusters
    op.create_table(
        'event_clusters',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('label', sa.String(length=256), nullable=True),
        sa.Column('representative_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('event_count', sa.Integer(), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('centroid_embedding', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_clusters_status', 'event_clusters', ['status'], unique=False)

    # 6. risk_signals
    op.create_table(
        'risk_signals',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('document_id', sa.String(length=64), nullable=False),
        sa.Column('event_cluster_id', sa.String(length=64), nullable=True),
        sa.Column('sentiment_label', sa.String(length=16), nullable=False),
        sa.Column('sentiment_score', sa.Float(), nullable=False),
        sa.Column('sentiment_confidence', sa.Float(), nullable=False),
        sa.Column('sentiment_probabilities', sa.JSON(), nullable=True),
        sa.Column('event_class', sa.String(length=64), nullable=False),
        sa.Column('event_confidence', sa.Float(), nullable=False),
        sa.Column('impact_score', sa.Float(), nullable=False),
        sa.Column('impact_components', sa.JSON(), nullable=True),
        sa.Column('risk_level', sa.String(length=16), nullable=False),
        sa.Column('overall_confidence', sa.Float(), nullable=False),
        sa.Column('novelty_score', sa.Float(), nullable=False),
        sa.Column('corroboration_score', sa.Float(), nullable=False),
        sa.Column('risk_trajectory', sa.String(length=32), nullable=True),
        sa.Column('source_name', sa.String(length=256), nullable=True),
        sa.Column('source_type', sa.String(length=64), nullable=True),
        sa.Column('source_credibility', sa.Float(), nullable=True),
        sa.Column('explanation', sa.JSON(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('market_context_available', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['event_cluster_id'], ['event_clusters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_signals_created_at', 'risk_signals', ['created_at'], unique=False)
    op.create_index('ix_risk_signals_event_class', 'risk_signals', ['event_class'], unique=False)
    op.create_index('ix_risk_signals_risk_level', 'risk_signals', ['risk_level'], unique=False)

    # 7. portfolios
    op.create_table(
        'portfolios',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('total_value', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. portfolio_positions
    op.create_table(
        'portfolio_positions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('portfolio_id', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=64), nullable=False),
        sa.Column('asset_class', sa.String(length=64), nullable=False),
        sa.Column('issuer', sa.String(length=256), nullable=True),
        sa.Column('ticker', sa.String(length=16), nullable=True),
        sa.Column('notional', sa.Float(), nullable=False),
        sa.Column('sector', sa.String(length=128), nullable=True),
        sa.Column('country', sa.String(length=64), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('credit_quality', sa.String(length=32), nullable=True),
        sa.Column('risk_weight', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. stress_scenarios
    op.create_table(
        'stress_scenarios',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('assumptions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 10. stress_simulations
    op.create_table(
        'stress_simulations',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('trigger_signal_id', sa.String(length=64), nullable=True),
        sa.Column('scenario_name', sa.String(length=128), nullable=False),
        sa.Column('portfolio_id', sa.String(length=64), nullable=True),
        sa.Column('portfolio_before', sa.Float(), nullable=False),
        sa.Column('portfolio_after', sa.Float(), nullable=False),
        sa.Column('absolute_loss', sa.Float(), nullable=False),
        sa.Column('loss_percentage', sa.Float(), nullable=False),
        sa.Column('asset_level_impacts', sa.JSON(), nullable=True),
        sa.Column('is_auto_triggered', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['trigger_signal_id'], ['risk_signals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stress_simulations_created_at', 'stress_simulations', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_stress_simulations_created_at', table_name='stress_simulations')
    op.drop_table('stress_simulations')
    op.drop_table('stress_scenarios')
    op.drop_table('portfolio_positions')
    op.drop_table('portfolios')
    op.drop_index('ix_risk_signals_risk_level', table_name='risk_signals')
    op.drop_index('ix_risk_signals_event_class', table_name='risk_signals')
    op.drop_index('ix_risk_signals_created_at', table_name='risk_signals')
    op.drop_table('risk_signals')
    op.drop_index('ix_event_clusters_status', table_name='event_clusters')
    op.drop_table('event_clusters')
    op.drop_table('document_entities')
    op.drop_index('ix_entities_ticker', table_name='entities')
    op.drop_index('ix_entities_canonical_name', table_name='entities')
    op.drop_table('entities')
    op.drop_table('documents')
    op.drop_table('sources')
