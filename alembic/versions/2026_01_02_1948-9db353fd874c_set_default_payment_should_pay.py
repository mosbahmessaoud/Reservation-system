"""set_default_payment_should_pay

Revision ID: 9db353fd874c
Revises: b44da44a6dc4
Create Date: 2026-01-02 19:48:54.622583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9db353fd874c'
down_revision: Union[str, None] = 'b44da44a6dc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Update all existing NULL values to 0.00
    op.execute("""
        UPDATE clan_settings 
        SET payment_should_pay = 0.00 
        WHERE payment_should_pay IS NULL
    """)

    # Step 2: Alter the column to set the default value (keeping nullable=True)
    op.alter_column('clan_settings', 'payment_should_pay',
                    existing_type=sa.Numeric(precision=15, scale=2),
                    server_default='0.00',
                    nullable=True)


def downgrade() -> None:
    # Remove the default constraint
    op.alter_column('clan_settings', 'payment_should_pay',
                    existing_type=sa.Numeric(precision=15, scale=2),
                    server_default=None,
                    nullable=True)
