from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.db.models.base import Base


class QRStatus(PyEnum):
    pending = "pending"  # ожидание
    completed = "completed"  # обработан
    canceled = "canceled"  # отменен
    in_processing = "in_processing"


class QRCode(Base):
    __tablename__ = "qr_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    qr_data: Mapped[str] = mapped_column(String, nullable=False)

    t: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    s: Mapped[float | None] = mapped_column(Float, nullable=True)
    fn: Mapped[str | None] = mapped_column(String, nullable=True)
    i: Mapped[str | None] = mapped_column(String, nullable=True)
    fp: Mapped[str | None] = mapped_column(String, nullable=True)
    n: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[QRStatus] = mapped_column(SAEnum(QRStatus), default=QRStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", backref="qr_codes")
