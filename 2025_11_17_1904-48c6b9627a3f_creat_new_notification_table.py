""" create new notification table with is_groom and general_notification

Revision ID: 48c6b9627a3f
Revises: 
Create Date: 2025-11-17 19:04:36.384472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '48c6b9627a3f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for notification types
    notification_type_enum = postgresql.ENUM(
        'new_reservation',
        'reservation_updated',
        'reservation_cancelled',
        'general_notification',
        name='notificationtype',
        create_type=False
    )

    # Try to create the enum type (if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationtype AS ENUM (
                'new_reservation',
                'reservation_updated',
                'reservation_cancelled',
                'general_notification'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reservation_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', notification_type_enum, nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('is_groom', sa.Boolean(),
                  nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reservation_id'], [
                                'reservations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('ix_notifications_id', 'notifications', ['id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_reservation_id',
                    'notifications', ['reservation_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at',
                    'notifications', ['created_at'])
    op.create_index('ix_notifications_notification_type',
                    'notifications', ['notification_type'])

    # Composite index for common query patterns
    op.create_index('ix_notifications_user_unread',
                    'notifications', ['user_id', 'is_read'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_notifications_user_unread', table_name='notifications')
    op.drop_index('ix_notifications_notification_type',
                  table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_reservation_id',
                  table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_notifications_id', table_name='notifications')

    # Drop table
    op.drop_table('notifications')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS notificationtype')
