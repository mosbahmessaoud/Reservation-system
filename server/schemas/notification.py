

# server\schemas\notification.py

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from ..models.notification import NotificationType


class NotificationBase(BaseModel):
    """Base notification schema"""
    notification_type: NotificationType
    title: str
    message: str


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    user_id: int
    reservation_id: int


class NotificationResponse(NotificationBase):
    """Schema for notification response"""
    id: int
    user_id: int
    reservation_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationWithReservation(NotificationResponse):
    """Notification with basic reservation info"""
    reservation: Optional[dict] = None

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    """Schema for updating notification"""
    is_read: Optional[bool] = None


class UnreadCountResponse(BaseModel):
    """Response for unread count"""
    unread_count: int


class NotificationBase(BaseModel):
    """Base notification schema"""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")


class NotificationCreate(NotificationBase):
    """Schema for creating a general notification"""
    user_id: int = Field(..., description="ID of the user to notify")
    reservation_id: int = Field(..., description="Related reservation ID")


class NotificationOut(NotificationBase):
    """Schema for notification output"""
    id: int
    user_id: int
    reservation_id: Optional[int] = None  # ← Make it optional
    notification_type: NotificationType
    is_read: bool
    is_groom: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    user_first_name: str
    user_last_name: str
    user_phone_number: str

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class NotificationMarkRead(BaseModel):
    """Schema for marking notification as read"""
    notification_id: int = Field(...,
                                 description="ID of the notification to mark as read")


class NotificationStats(BaseModel):
    """Schema for notification statistics"""
    unread_count: int = Field(...,
                              description="Number of unread notifications")
    total_count: int = Field(..., description="Total number of notifications")
    by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of unread notifications by type"
    )


class BulkNotificationResponse(BaseModel):
    """Schema for bulk operations response"""
    message: str = Field(..., description="Operation result message")
    count: int = Field(..., description="Number of notifications affected")
    success: bool = Field(..., description="Whether operation was successful")


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list"""
    notifications: list[NotificationOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class NotifDataCreat(BaseModel):  # Inherit from BaseModel for Pydantic validation
    title: str
    message: str
    is_groom: bool
