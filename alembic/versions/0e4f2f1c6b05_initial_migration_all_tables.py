"""Initial migration - all tables

Revision ID: 0e4f2f1c6b05
Revises: 
Create Date: 2025-11-17 22:47:07.691284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '0e4f2f1c6b05'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create counties table
    op.create_table(
        'counties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_counties_id'), 'counties', ['id'], unique=False)

    # Create clans table
    op.create_table(
        'clans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('county_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['county_id'], ['counties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clans_id'), 'clans', ['id'], unique=False)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('super_admin', 'clan_admin',
                  'groom', name='userrole'), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('father_name', sa.String(), nullable=False),
        sa.Column('grandfather_name', sa.String(), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('birth_address', sa.String(), nullable=True),
        sa.Column('home_address', sa.String(), nullable=True),
        sa.Column('phone_verified', sa.Boolean(), nullable=True),
        sa.Column('otp_code', sa.String(), nullable=True),
        sa.Column('otp_expiration', sa.DateTime(), nullable=True),
        sa.Column('temp_phone_number', sa.String(), nullable=True),
        sa.Column('temp_phone_otp_code', sa.String(), nullable=True),
        sa.Column('temp_phone_otp_expires_at', sa.DateTime(), nullable=True),
        sa.Column('clan_id', sa.Integer(), nullable=True),
        sa.Column('county_id', sa.Integer(), nullable=True),
        sa.Column('guardian_name', sa.String(), nullable=True),
        sa.Column('guardian_phone', sa.String(), nullable=True),
        sa.Column('guardian_relation', sa.String(), nullable=True),
        sa.Column('guardian_birth_date', sa.Date(), nullable=True),
        sa.Column('guardian_birth_address', sa.String(), nullable=True),
        sa.Column('guardian_home_address', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive',
                  name='userstatus'), nullable=False),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ),
        sa.ForeignKeyConstraint(['county_id'], ['counties.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_phone_number'),
                    'users', ['phone_number'], unique=True)

    # Create halls_table
    op.create_table(
        'halls_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('clan_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_halls_table_id'),
                    'halls_table', ['id'], unique=False)

    # Create clan_settings table
    op.create_table(
        'clan_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clan_id', sa.Integer(), nullable=False),
        sa.Column('allow_cross_clan_reservations',
                  sa.Boolean(), nullable=True),
        sa.Column('max_grooms_per_date', sa.Integer(), nullable=True),
        sa.Column('allow_two_day_reservations', sa.Boolean(), nullable=True),
        sa.Column('validation_deadline_days', sa.Integer(), nullable=True),
        sa.Column('allowed_months_single_day', sa.String(), nullable=True),
        sa.Column('allowed_months_two_day', sa.String(), nullable=True),
        sa.Column('calendar_years_ahead', sa.Integer(), nullable=True),
        sa.Column('days_to_accept_invites', sa.String(), nullable=True),
        sa.Column('accept_invites_times', sa.String(), nullable=True),
        sa.Column('years_max_reserv_GroomFromOutClan',
                  sa.Integer(), nullable=True),
        sa.Column('years_max_reserv_GrooomFromOriginClan',
                  sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clan_id')
    )
    op.create_index(op.f('ix_clan_settings_id'),
                    'clan_settings', ['id'], unique=False)

    # Create clan_rules table
    op.create_table(
        'clan_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('general_rule', sa.Text(), nullable=True),
        sa.Column('groom_supplies', sa.Text(), nullable=True),
        sa.Column('rule_about_clothing', sa.Text(), nullable=True),
        sa.Column('rule_about_kitchenware', sa.Text(), nullable=True),
        sa.Column('rules_book_of_clan_pdf', sa.Text(), nullable=True),
        sa.Column('clan_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clan_rules_id'),
                    'clan_rules', ['id'], unique=False)

    # Create food_menus table
    op.create_table(
        'food_menus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_type', sa.String(length=50), nullable=False),
        sa.Column('number_of_visitors', sa.Integer(), nullable=False),
        sa.Column('menu_details', JSON, nullable=False),
        sa.Column('clan_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_food_menus_id'),
                    'food_menus', ['id'], unique=False)

    # Create haia_committee table
    op.create_table(
        'haia_committee',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('county_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['county_id'], ['counties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_haia_committee_id'),
                    'haia_committee', ['id'], unique=False)

    # Create madaeh_committees table
    op.create_table(
        'madaeh_committees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('county_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['county_id'], ['counties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_madaeh_committees_id'),
                    'madaeh_committees', ['id'], unique=False)

    # Create reservations table
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('groom_id', sa.Integer(), nullable=True),
        sa.Column('clan_id', sa.Integer(), nullable=False),
        sa.Column('county_id', sa.Integer(), nullable=False),
        sa.Column('date1', sa.Date(), nullable=False),
        sa.Column('date2', sa.Date(), nullable=True),
        sa.Column('date2_bool', sa.Boolean(), nullable=True),
        sa.Column('allow_others', sa.Boolean(), nullable=False),
        sa.Column('join_to_mass_wedding', sa.Boolean(), nullable=False),
        sa.Column('status', sa.Enum('pending_validation', 'validated',
                  'cancelled', name='reservationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('payment_valid', sa.Boolean(), nullable=True),
        sa.Column('hall_id', sa.Integer(), nullable=True),
        sa.Column('haia_committee_id', sa.Integer(), nullable=True),
        sa.Column('madaeh_committee_id', sa.Integer(), nullable=True),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('father_name', sa.String(), nullable=True),
        sa.Column('grandfather_name', sa.String(), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('birth_address', sa.String(), nullable=True),
        sa.Column('home_address', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('guardian_name', sa.String(), nullable=True),
        sa.Column('guardian_phone', sa.String(), nullable=True),
        sa.Column('guardian_home_address', sa.String(), nullable=True),
        sa.Column('guardian_birth_address', sa.String(), nullable=True),
        sa.Column('guardian_birth_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ),
        sa.ForeignKeyConstraint(['county_id'], ['counties.id'], ),
        sa.ForeignKeyConstraint(
            ['groom_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['hall_id'], ['halls_table.id'], ),
        sa.ForeignKeyConstraint(['haia_committee_id'], [
                                'haia_committee.id'], ),
        sa.ForeignKeyConstraint(['madaeh_committee_id'], [
                                'madaeh_committees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservations_id'),
                    'reservations', ['id'], unique=False)

    # Create reservations_special table
    op.create_table(
        'reservations_special',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clan_id', sa.Integer(), nullable=False),
        sa.Column('county_id', sa.Integer(), nullable=False),
        sa.Column('reserv_name', sa.String(), nullable=False),
        sa.Column('reserv_desctiption', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('home_address', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('validated', 'cancelled',
                  name='reservationspecialstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['clan_id'], ['clans.id'], ),
        sa.ForeignKeyConstraint(['county_id'], ['counties.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservations_special_id'),
                    'reservations_special', ['id'], unique=False)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reservation_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.Enum('new_reservation', 'reservation_updated',
                  'reservation_cancelled', 'general_notification', name='notificationtype'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('is_groom', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['reservation_id'], [
                                'reservations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'),
                    'notifications', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')

    op.drop_index(op.f('ix_reservations_special_id'),
                  table_name='reservations_special')
    op.drop_table('reservations_special')

    op.drop_index(op.f('ix_reservations_id'), table_name='reservations')
    op.drop_table('reservations')

    op.drop_index(op.f('ix_madaeh_committees_id'),
                  table_name='madaeh_committees')
    op.drop_table('madaeh_committees')

    op.drop_index(op.f('ix_haia_committee_id'), table_name='haia_committee')
    op.drop_table('haia_committee')

    op.drop_index(op.f('ix_food_menus_id'), table_name='food_menus')
    op.drop_table('food_menus')

    op.drop_index(op.f('ix_clan_rules_id'), table_name='clan_rules')
    op.drop_table('clan_rules')

    op.drop_index(op.f('ix_clan_settings_id'), table_name='clan_settings')
    op.drop_table('clan_settings')

    op.drop_index(op.f('ix_halls_table_id'), table_name='halls_table')
    op.drop_table('halls_table')

    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

    op.drop_index(op.f('ix_clans_id'), table_name='clans')
    op.drop_table('clans')

    op.drop_index(op.f('ix_counties_id'), table_name='counties')
    op.drop_table('counties')

    # Drop enums
    sa.Enum(name='notificationtype').drop(op.get_bind())
    sa.Enum(name='reservationspecialstatus').drop(op.get_bind())
    sa.Enum(name='reservationstatus').drop(op.get_bind())
    sa.Enum(name='userstatus').drop(op.get_bind())
    sa.Enum(name='userrole').drop(op.get_bind())
