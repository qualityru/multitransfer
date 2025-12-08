from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.db.models.base import Base


class TransactionType(PyEnum):
    deposit = "deposit"
    withdraw = "withdraw"
    refund = "refund"  # возврат средств (например, при отмене вывода)
    adjust = "adjust"  # ручная корректировка админом
    qr_scan = "qr_scan"


class TransactionStatus(PyEnum):
    pending = "pending"  # пользователь создал заявку
    canceled = "canceled"  # отменено
    completed = "completed"  # полностью завершено
    in_processing = "in_processing"  # обрабатывается


class NetworkType(str, PyEnum):
    trc20 = "trc20"
    erc20 = "erc20"
    bep20 = "bep20"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType), nullable=False
    )

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus), default=TransactionStatus.pending
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)

    related_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", backref="transactions")


class Balance(Base):
    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(5), default="USDT")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", backref="balance")


class Withdraw(Base):
    __tablename__ = "withdraws"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    amount: Mapped[float] = mapped_column(nullable=False)

    usdt_wallet: Mapped[str] = mapped_column(String(100))
    network: Mapped[NetworkType] = mapped_column(SAEnum(NetworkType), nullable=False)

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus), default=TransactionStatus.pending
    )
    hash: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WithdrawalSettings(Base):
    __tablename__ = "withdrawal_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    network: Mapped[NetworkType] = mapped_column(
        SAEnum(NetworkType), unique=True, nullable=False
    )
    fee: Mapped[float] = mapped_column(nullable=False)
