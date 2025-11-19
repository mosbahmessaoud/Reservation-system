# Path: server\utils\notification_service.py

from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from server.models.notification import Notification, NotificationType
from server.models.user import User, UserRole
from server.models.reservation import Reservation


class NotificationService:
    """Service to handle notification creation and management"""

    @staticmethod
    def create_new_reservation_notification(
        db: Session,
        reservation: Reservation
    ) -> Optional[Notification]:
        """
        Create notification for clan admin when a new reservation is made.

        Args:
            db: Database session
            reservation: The newly created reservation

        Returns:
            Created Notification object or None
        """
        # Find the clan admin for this clan
        clan_admin = db.query(User).filter(
            User.clan_id == reservation.clan_id,
            User.role == UserRole.clan_admin
        ).first()

        if not clan_admin:
            print(
                f"Warning: No clan admin found for clan_id {reservation.clan_id}")
            return None

        # Get groom's name
        groom_name = "Unknown"
        if reservation.groom:
            groom_name = f"{reservation.groom.first_name} {reservation.groom.last_name}"
        elif reservation.first_name and reservation.last_name:
            groom_name = f"{reservation.first_name} {reservation.last_name}"

        # Create notification
        notification = Notification(
            user_id=clan_admin.id,
            reservation_id=reservation.id,
            notification_type=NotificationType.new_reservation,
            title="حجز جديد",
            message=f"تم إنشاء حجز جديد من قبل {groom_name} بتاريخ {reservation.date1.strftime('%Y-%m-%d')} \n {reservation.phone_number} رقم الهاتف: ",
            is_read=False,
            is_groom=False,
            created_at=datetime.utcnow()
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    @staticmethod
    def create_reservation_updated_notification(
        db: Session,
        reservation: Reservation,
        update_details: str = "",
        notify_groom: bool = False
    ) -> Optional[Notification]:
        """
        Create notification when reservation is updated.

        Args:
            db: Database session
            reservation: The updated reservation
            update_details: Details about what was updated
            notify_groom: If True, notify the groom instead of clan admin
        """
        if notify_groom:
            # Notify the groom about the update
            target_user = reservation.groom
            if not target_user:
                return None

            notification = Notification(
                user_id=target_user.id,
                reservation_id=reservation.id,
                notification_type=NotificationType.reservation_updated,
                title="تحديث حجز - Reservation Updated",
                message=f"تم تحديث حجزك رقم {reservation.id}. {update_details}",
                is_read=False,
                is_groom=True,
                created_at=datetime.utcnow()
            )
        else:
            # Notify the clan admin
            clan_admin = db.query(User).filter(
                User.clan_id == reservation.clan_id,
                User.role == UserRole.clan_admin
            ).first()

            if not clan_admin:
                return None

            notification = Notification(
                user_id=clan_admin.id,
                reservation_id=reservation.id,
                notification_type=NotificationType.reservation_updated,
                title="تحديث حجز - Reservation Updated",
                message=f"تم تحديث الحجز رقم {reservation.id}. {update_details}",
                is_read=False,
                is_groom=False,
                created_at=datetime.utcnow()
            )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    @staticmethod
    def create_reservation_cancelled_notification(
        db: Session,
        reservation: Reservation,
        notify_groom: bool = False
    ) -> Optional[Notification]:
        """
        Create notification when reservation is cancelled.

        Args:
            db: Database session
            reservation: The cancelled reservation
            notify_groom: If True, notify the groom instead of clan admin
        """
        if notify_groom:
            # Notify the groom about cancellation
            target_user = reservation.groom
            if not target_user:
                return None

            notification = Notification(
                user_id=target_user.id,
                reservation_id=reservation.id,
                notification_type=NotificationType.reservation_cancelled,
                title="إلغاء حجز - Reservation Cancelled",
                message=f"تم إلغاء حجزك رقم {reservation.id}",
                is_read=False,
                is_groom=True,
                created_at=datetime.utcnow()
            )
        else:
            # Notify the clan admin
            clan_admin = db.query(User).filter(
                User.clan_id == reservation.clan_id,
                User.role == UserRole.clan_admin
            ).first()

            if not clan_admin:
                return None

            notification = Notification(
                user_id=clan_admin.id,
                reservation_id=reservation.id,
                notification_type=NotificationType.reservation_cancelled,
                title="إلغاء حجز - Reservation Cancelled",
                message=f"تم إلغاء الحجز رقم {reservation.id}",
                is_read=False,
                is_groom=False,
                created_at=datetime.utcnow()
            )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    @staticmethod
    def create_general_notification(
        db: Session,
        user_id: int,
        reservation_id: int,
        title: str,
        message: str,
        is_groom: bool = False
    ) -> Optional[Notification]:
        """
        Create a general notification for a user.

        Args:
            db: Database session
            user_id: ID of the user to notify
            reservation_id: Related reservation ID
            title: Notification title
            message: Notification message
            is_groom: Whether the notification is for a groom
        """
        notification = Notification(
            user_id=user_id,
            reservation_id=reservation_id,
            notification_type=NotificationType.general_notification,
            title=title,
            message=message,
            is_read=False,
            is_groom=is_groom,
            created_at=datetime.utcnow()
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    @staticmethod
    def mark_notification_as_read(
        db: Session,
        notification_id: int,
        user_id: int
    ) -> bool:
        """Mark a notification as read"""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if notification:
            notification.mark_as_read()
            db.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(
        db: Session,
        user_id: int
    ) -> int:
        """Mark all notifications as read for a user"""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        db.commit()
        return count

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ):
        """Get notifications for a user"""
        query = db.query(Notification).filter(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        return query.order_by(
            Notification.created_at.desc()
        ).limit(limit).all()

    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """Get count of unread notifications"""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

    @staticmethod
    def notify_reservation_validation(
        db: Session,
        reservation: Reservation,
        is_approved: bool
    ) -> Optional[Notification]:
        """
        Notify groom when their reservation is validated or rejected.

        Args:
            db: Database session
            reservation: The reservation that was validated/rejected
            is_approved: True if approved, False if rejected
        """
        if not reservation.groom:
            return None

        if is_approved:
            title = "تم تأكيد الحجز - Reservation Approved"
            message = f"تم تأكيد حجزك رقم {reservation.id} بنجاح"
        else:
            title = "تم رفض الحجز - Reservation Rejected"
            message = f"تم رفض حجزك رقم {reservation.id}"

        notification = Notification(
            user_id=reservation.groom_id,
            reservation_id=reservation.id,
            notification_type=NotificationType.general_notification,
            title=title,
            message=message,
            is_read=False,
            is_groom=True,
            created_at=datetime.utcnow()
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification
