# server\routes\notifications.py
"""
Notification routes for grooms and clan admins.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from server.auth_utils import get_current_user, get_db, require_role
from server.models.user import User, UserRole
from server.models.notification import Notification, NotificationType
from server.models.reservation import Reservation
from server.utils.notification_service import NotificationService
from server.schemas.notification import (
    NotifDataCreat,
    NotificationOut,
    NotificationCreate,
    NotificationMarkRead,
    NotificationStats,
    BulkNotificationResponse
)
from server.routes.auth import super_admin_required

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

# Role-based dependencies
groom_required = require_role([UserRole.groom,  UserRole.super_admin])
clan_admin_required = require_role([UserRole.clan_admin, UserRole.super_admin])
authenticated = require_role(
    [UserRole.groom, UserRole.clan_admin, UserRole.super_admin])


# @router.get("", response_model=List[NotificationOut])
# def get_notifications(
#     unread_only: bool = Query(
#         False, description="Get only unread notifications"),
#     limit: int = Query(
#         50, ge=1, le=100, description="Maximum number of notifications to return"),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(authenticated)
# ):
#     """
#     Get all notifications for the current user.

#     - **unread_only**: Filter to show only unread notifications
#     - **limit**: Maximum number of notifications to return (1-100)
#     """
#     try:
#         notifications = NotificationService.get_user_notifications(
#             db=db,
#             user_id=current_user.id,
#             unread_only=unread_only,
#             limit=limit
#         )

#         logger.info(
#             f"Retrieved {len(notifications)} notifications for user {current_user.id}")
#         return notifications

#     except Exception as e:
#         logger.error(
#             f"Error retrieving notifications for user {current_user.id}: {e}")
#         raise HTTPException(500, f"خطأ في جلب الإشعارات: {str(e)}")
"""
Fixed notification routes - NO MODEL CHANGES NEEDED
Replace the get_notifications endpoint in server/routes/notifications.py
"""


@router.get("", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = Query(
        False, description="Get only unread notifications"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of notifications to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """Get all notifications for the current user."""
    try:
        query = db.query(Notification).filter(
            Notification.user_id == current_user.id
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        notifications = query.order_by(
            Notification.created_at.desc()
        ).limit(limit).all()

        logger.info(
            f"Retrieved {len(notifications)} notifications for user {current_user.id}")

        # Manually serialize each notification
        result = []
        for notif in notifications:
            try:
                notification_dict = {
                    "id": notif.id,
                    "user_id": notif.user_id,
                    "reservation_id": notif.reservation_id,  # Can be None now
                    "notification_type": notif.notification_type,
                    "title": notif.title,
                    "message": notif.message,
                    "is_read": notif.is_read,
                    "is_groom": notif.is_groom,
                    "created_at": notif.created_at,
                    "read_at": notif.read_at
                }
                result.append(NotificationOut(**notification_dict))
            except Exception as serialize_error:
                logger.error(
                    f"Error serializing notification {notif.id}: {serialize_error}")
                continue

        return result

    except Exception as e:
        logger.error(
            f"Error retrieving notifications for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "خطأ في جلب الإشعارات",
                "message": str(e),
                "type": "database_error"
            }
        )

# Also update the get_notification_stats endpoint


@router.get("/stats", response_model=NotificationStats)
def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Get notification statistics for the current user.

    Returns:
    - Total count of unread notifications
    - Breakdown by notification type
    """
    try:
        # Count unread notifications
        unread_count = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).count()

        # Get breakdown by type - avoid loading relationships
        notifications = db.query(
            Notification.notification_type
        ).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).all()

        type_breakdown = {}
        for (notif_type,) in notifications:
            type_value = notif_type.value if hasattr(
                notif_type, 'value') else str(notif_type)
            type_breakdown[type_value] = type_breakdown.get(type_value, 0) + 1

        logger.info(
            f"Stats retrieved for user {current_user.id}: {unread_count} unread")

        return NotificationStats(
            unread_count=unread_count,
            total_count=len(notifications),
            by_type=type_breakdown
        )

    except Exception as e:
        logger.error(
            f"Error getting notification stats for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "خطأ في جلب إحصائيات الإشعارات",
                "message": str(e)
            }
        )


# Fix the get_notifications_by_reservation endpoint
@router.get("/by-reservation/{reservation_id}", response_model=List[NotificationOut])
def get_notifications_by_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Get all notifications for a specific reservation.
    """
    try:
        # Get notifications without loading relationships
        notifications = db.query(Notification).filter(
            Notification.reservation_id == reservation_id
        ).order_by(
            Notification.created_at.desc()
        ).all()

        # Filter based on user permissions
        allowed_notifications = []

        for notif in notifications:
            # If it's the user's own notification
            if notif.user_id == current_user.id:
                allowed_notifications.append(notif)
            # If user is clan admin, check reservation clan
            elif current_user.role == UserRole.clan_admin:
                # Query reservation separately to avoid relationship issues
                reservation = db.query(Reservation).filter(
                    Reservation.id == reservation_id
                ).first()
                if reservation and reservation.clan_id == current_user.clan_id:
                    allowed_notifications.append(notif)

        # Manually serialize
        result = []
        for notif in allowed_notifications:
            try:
                result.append(NotificationOut(
                    id=notif.id,
                    user_id=notif.user_id,
                    reservation_id=notif.reservation_id,
                    notification_type=notif.notification_type,
                    title=notif.title,
                    message=notif.message,
                    is_read=notif.is_read,
                    is_groom=notif.is_groom,
                    created_at=notif.created_at,
                    read_at=notif.read_at
                ))
            except Exception as serialize_error:
                logger.error(
                    f"Error serializing notification {notif.id}: {serialize_error}")
                continue

        logger.info(
            f"Retrieved {len(result)} notifications for "
            f"reservation {reservation_id}, user {current_user.id}"
        )

        return result

    except Exception as e:
        logger.error(
            f"Error retrieving notifications for reservation {reservation_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "خطأ في جلب الإشعارات",
                "message": str(e)
            }
        )


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Get the count of unread notifications for quick polling.

    Returns:
    - count: Number of unread notifications
    """
    try:
        count = NotificationService.get_unread_count(
            db=db,
            user_id=current_user.id
        )

        return {"count": count}

    except Exception as e:
        logger.error(
            f"Error getting unread count for user {current_user.id}: {e}")
        raise HTTPException(500, f"خطأ في جلب عدد الإشعارات: {str(e)}")


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification_by_id(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Get a specific notification by ID.

    - **notification_id**: The ID of the notification to retrieve
    """
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(404, "الإشعار غير موجود")

        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving notification {notification_id}: {e}")
        raise HTTPException(500, f"خطأ في جلب الإشعار: {str(e)}")


@router.patch("/{notification_id}/read", response_model=dict)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Mark a specific notification as read.

    - **notification_id**: The ID of the notification to mark as read
    """
    try:
        success = NotificationService.mark_notification_as_read(
            db=db,
            notification_id=notification_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(404, "الإشعار غير موجود")

        logger.info(
            f"Notification {notification_id} marked as read by user {current_user.id}")

        return {
            "message": "تم تعليم الإشعار كمقروء",
            "notification_id": notification_id,
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error marking notification {notification_id} as read: {e}")
        raise HTTPException(500, f"خطأ في تعليم الإشعار كمقروء: {str(e)}")


@router.patch("/mark-all-read", response_model=BulkNotificationResponse)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Mark all notifications as read for the current user.
    """
    try:
        count = NotificationService.mark_all_as_read(
            db=db,
            user_id=current_user.id
        )

        logger.info(
            f"Marked {count} notifications as read for user {current_user.id}")

        return {
            "message": f"تم تعليم {count} إشعار كمقروء",
            "count": count,
            "success": True
        }

    except Exception as e:
        logger.error(
            f"Error marking all notifications as read for user {current_user.id}: {e}")
        raise HTTPException(500, f"خطأ في تعليم الإشعارات كمقروءة: {str(e)}")


@router.delete("/{notification_id}", response_model=dict)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Delete a specific notification.

    - **notification_id**: The ID of the notification to delete
    """
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(404, "الإشعار غير موجود")

        db.delete(notification)
        db.commit()

        logger.info(
            f"Notification {notification_id} deleted by user {current_user.id}")

        return {
            "message": "تم حذف الإشعار",
            "notification_id": notification_id,
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {e}")
        db.rollback()
        raise HTTPException(500, f"خطأ في حذف الإشعار: {str(e)}")


@router.delete("/bulk-delete", response_model=BulkNotificationResponse)
def bulk_delete_notifications(
    notification_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Delete multiple notifications at once.

    - **notification_ids**: List of notification IDs to delete
    """
    try:
        if not notification_ids:
            raise HTTPException(400, "قائمة معرفات الإشعارات فارغة")

        count = db.query(Notification).filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == current_user.id
        ).delete(synchronize_session=False)

        db.commit()

        logger.info(
            f"Deleted {count} notifications for user {current_user.id}")

        return {
            "message": f"تم حذف {count} إشعار",
            "count": count,
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk deleting notifications: {e}")
        db.rollback()
        raise HTTPException(500, f"خطأ في حذف الإشعارات: {str(e)}")


# # Admin-only routes
# @router.post("/create-general", response_model=NotificationOut, dependencies=[Depends(clan_admin_required)])
# def create_general_notification(
#     notification_data: NotificationCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(clan_admin_required)
# ):
#     """
#     Create a general notification (Clan Admin only).

#     Allows clan admins to send custom notifications to users.
#     """
#     try:
#         # Verify the reservation belongs to the admin's clan
#         reservation = db.query(Reservation).filter(
#             Reservation.id == notification_data.reservation_id
#         ).first()

#         if not reservation:
#             raise HTTPException(404, "الحجز غير موجود")

#         if reservation.clan_id != current_user.clan_id:
#             raise HTTPException(403, "غير مصرح لك بإرسال إشعارات لهذا الحجز")

#         # Verify the target user
#         target_user = db.query(User).filter(
#             User.id == notification_data.user_id
#         ).first()

#         if not target_user:
#             raise HTTPException(404, "المستخدم المستهدف غير موجود")

#         # Create the notification
#         notification = NotificationService.create_general_notification(
#             db=db,
#             user_id=notification_data.user_id,
#             reservation_id=notification_data.reservation_id,
#             title=notification_data.title,
#             message=notification_data.message,
#             is_groom=(target_user.role == UserRole.groom)
#         )

#         if not notification:
#             raise HTTPException(500, "فشل إنشاء الإشعار")

#         logger.info(
#             f"General notification created by admin {current_user.id} for user {notification_data.user_id}")

#         return notification

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error creating general notification: {e}")
#         db.rollback()
#         raise HTTPException(500, f"خطأ في إنشاء الإشعار: {str(e)}")


@router.post("/notify-validation/{reservation_id}", response_model=NotificationOut, dependencies=[Depends(clan_admin_required)])
def notify_reservation_validation(
    reservation_id: int,
    is_approved: bool = Query(...,
                              description="True if approved, False if rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(clan_admin_required)
):
    """
    Send validation notification to groom (Clan Admin only).

    - **reservation_id**: The ID of the reservation
    - **is_approved**: Whether the reservation was approved or rejected
    """
    try:
        # Get the reservation
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise HTTPException(404, "الحجز غير موجود")

        # Verify admin has permission
        if reservation.clan_id != current_user.clan_id:
            raise HTTPException(403, "غير مصرح لك بالتعامل مع هذا الحجز")

        # Create validation notification
        notification = NotificationService.notify_reservation_validation(
            db=db,
            reservation=reservation,
            is_approved=is_approved
        )

        if not notification:
            raise HTTPException(500, "فشل إنشاء إشعار التحقق")

        logger.info(
            f"Validation notification sent for reservation {reservation_id}, approved: {is_approved}")

        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending validation notification: {e}")
        db.rollback()
        raise HTTPException(500, f"خطأ في إرسال إشعار التحقق: {str(e)}")


@router.get("/by-type/{notification_type}", response_model=List[NotificationOut])
def get_notifications_by_type(
    notification_type: NotificationType,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Get notifications filtered by type.

    - **notification_type**: Type of notifications to retrieve
    - **limit**: Maximum number of notifications to return
    """
    try:
        notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.notification_type == notification_type
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit).all()

        logger.info(
            f"Retrieved {len(notifications)} notifications of type {notification_type} for user {current_user.id}")

        return notifications

    except Exception as e:
        logger.error(f"Error getting notifications by type: {e}")
        raise HTTPException(500, f"خطأ في جلب الإشعارات: {str(e)}")

    # Add this route to your notifications.py file in the FastAPI backend


# Alternative: Simpler version if you want to allow any authenticated user
# to see notifications for a reservation (less secure but simpler)

@router.get("/by-reservation/{reservation_id}/latest", response_model=NotificationOut)
def get_latest_notification_for_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(authenticated)
):
    """
    Get the most recent notification for a specific reservation.

    Useful for fetching the auto-generated notification immediately after 
    creating a reservation.

    - **reservation_id**: The ID of the reservation
    """
    try:
        # Get the most recent notification for this reservation
        notification = db.query(Notification).filter(
            Notification.reservation_id == reservation_id
        ).order_by(
            Notification.created_at.desc()
        ).first()

        if not notification:
            raise HTTPException(
                404,
                f"لا توجد إشعارات للحجز رقم {reservation_id}"
            )

        # Security check
        if notification.user_id != current_user.id:
            if current_user.role == UserRole.clan_admin:
                reservation = db.query(Reservation).filter(
                    Reservation.id == reservation_id
                ).first()
                if not reservation or reservation.clan_id != current_user.clan_id:
                    raise HTTPException(
                        403,
                        "غير مصرح لك بالوصول إلى هذا الإشعار"
                    )
            else:
                raise HTTPException(
                    403,
                    "غير مصرح لك بالوصول إلى هذا الإشعار"
                )

        logger.info(
            f"Retrieved latest notification (ID: {notification.id}) for "
            f"reservation {reservation_id}, user {current_user.id}"
        )

        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving latest notification for reservation {reservation_id}: {e}"
        )
        raise HTTPException(
            500,
            f"خطأ في جلب الإشعار: {str(e)}"
        )


# create general notification
@router.post("/create_notification", dependencies=[Depends(super_admin_required)])
def create_notification(notif_data: NotifDataCreat, db: Session = Depends(get_db)):
    # Get all users from the database
    users = db.query(User).filter(
        User.role == (
            UserRole.groom if notif_data.is_groom else UserRole.clan_admin)
    ).all()  # Replace 'User' with your actual user model

    # Create notification for each user
    for user in users:
        NotificationService.create_general_notification(
            db=db,
            user_id=user.id,
            title=notif_data.title,
            message=notif_data.message,
            is_groom=notif_data.is_groom
        )

    return {"message": f"Notification sent to {len(users)} users successfully"}

# # create general notification
# @router.post("/create_notification_grooms_reserved", dependencies=[Depends(super_admin_required)])
# def create_notification(notif_data: NotifDataCreat, db: Session = Depends(get_db)):
#     # Get all users from the database
#     users = db.query(User).filter(
#         User.role == UserRole.groom
#     ).all()  # Replace 'User' with your actual user model

#     # Create notification for each user
#     for user in users:
#         NotificationService.create_general_notification(
#             db=db,
#             user_id=user.id,
#             title=notif_data.title,
#             message=notif_data.message,
#             is_groom=True
#         )

#     return {"message": f"Notification sent to {len(users)} users successfully"}
