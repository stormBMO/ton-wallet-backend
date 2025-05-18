"""create_token_risks_table

Revision ID: 3aa8e23979f3
Revises: 449d739d685f
Create Date: 2025-05-18 23:29:55.661019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision: str = '3aa8e23979f3'
down_revision: Union[str, None] = '449d739d685f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('token_risks',
    sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sa.Column('token_id', sa.String(), nullable=False, unique=True, index=True),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('volatility_30d', sa.Float(), nullable=True),
    sa.Column('liquidity_score', sa.Float(), nullable=True),
    sa.Column('sentiment_score', sa.Float(), nullable=True),
    sa.Column('contract_risk_score', sa.Float(), nullable=True),
    sa.Column('overall_risk_score', sa.Float(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('token_risks')
