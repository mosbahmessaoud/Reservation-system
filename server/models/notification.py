"""
Notification model: Stores notifications for clan admins about new reservations.
Path: server/models/notification.py
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..db import Base


class NotificationType(str, enum.Enum):
    new_reservation = "new_reservation"
    reservation_updated = "reservation_updated"
    reservation_cancelled = "reservation_cancelled"
    general_notification = "general_notification"  # new column


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # The admin who should receive this notification
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    # The reservation that triggered this notification
    reservation_id = Column(Integer, ForeignKey(
        "reservations.id", ondelete="CASCADE"), nullable=True)
 
    # Notification details
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    # Status tracking
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)

    # groom or clan admin
    is_groom = Column(Boolean, default=False, nullable=False)  # new column

    # Relationships
    user = relationship("User", backref="notifications", lazy="select")
    reservation = relationship(
        "Reservation", backref="notifications", lazy="select")

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
