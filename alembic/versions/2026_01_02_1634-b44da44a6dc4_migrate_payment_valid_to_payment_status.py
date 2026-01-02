"""migrate payment_valid to payment_status

Revision ID: b44da44a6dc4
Revises: e6e3bbd3e5ac
Create Date: 2026-01-02 16:34:55.404425

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b44da44a6dc4'
down_revision: Union[str, None] = 'e6e3bbd3e5ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add payment_should_pay to clan_settings
    op.add_column('clan_settings', sa.Column('payment_should_pay',
                  sa.Numeric(precision=15, scale=2), nullable=True))

    # Step 2: CREATE the enum type FIRST (this was missing!)
    payment_status_enum = sa.Enum(
        'paid', 'not_paid', 'partially_paid', name='paymentstatus')
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    # Step 3: Add payment_status column as NULLABLE first (to allow data migration)
    op.add_column('reservations', sa.Column('payment_status',
                  sa.Enum('paid', 'not_paid', 'partially_paid',
                          name='paymentstatus'),
                  nullable=True))

    # Step 4: Migrate existing data from payment_valid to payment_status
    # payment_valid = True → payment_status = 'paid'
    op.execute("""
        UPDATE reservations 
        SET payment_status = 'paid' 
        WHERE payment_valid = TRUE
    """)

    # payment_valid = False → payment_status = 'not_paid'
    op.execute("""
        UPDATE reservations 
        SET payment_status = 'not_paid' 
        WHERE payment_valid = FALSE
    """)

    # payment_valid = NULL → payment_status = 'not_paid'
    op.execute("""
        UPDATE reservations 
        SET payment_status = 'not_paid' 
        WHERE payment_valid IS NULL
    """)

    # Step 5: Now make payment_status NOT NULL after data migration
    op.alter_column('reservations', 'payment_status', nullable=False)

    # Step 6: Add payment column
    op.add_column('reservations', sa.Column(
        'payment', sa.Numeric(precision=15, scale=2), nullable=True))

    # Step 7: Drop the old payment_valid column
    op.drop_column('reservations', 'payment_valid')


def downgrade() -> None:
    # Add back payment_valid column
    op.add_column('reservations', sa.Column('payment_valid',
                  sa.BOOLEAN(), autoincrement=False, nullable=True))

    # Migrate data back from payment_status to payment_valid
    # payment_status = 'paid' → payment_valid = True
    op.execute("""
        UPDATE reservations 
        SET payment_valid = TRUE 
        WHERE payment_status = 'paid'
    """)

    # payment_status = 'not_paid' or 'partially_paid' → payment_valid = False
    op.execute("""
        UPDATE reservations 
        SET payment_valid = FALSE 
        WHERE payment_status IN ('not_paid', 'partially_paid')
    """)

    # Drop columns
    op.drop_column('reservations', 'payment')
    op.drop_column('reservations', 'payment_status')
    op.drop_column('clan_settings', 'payment_should_pay')

    # Drop the enum type
    sa.Enum(name='paymentstatus').drop(op.get_bind(), checkfirst=True)
