from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.db.models.base import Base, TimestampMixin


class TempOTPStorage(TimestampMixin, Base):
    __tablename__ = "temp_otp_storage"

    subject: Mapped[str] = mapped_column(String)
    otp_code: Mapped[str] = mapped_column(String, nullable=True)
    confirmed: Mapped[bool] = mapped_column(default=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    enable: Mapped[bool] = mapped_column(default=True)

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", uselist=False, back_populates="user", lazy="selectin"
    )
    auths: Mapped[list["UserAuth"]] = relationship(
        "UserAuth",
        uselist=True,
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def auths_map(self):
        if self.auths:
            return {auth.provider.slug: auth.subject for auth in self.auths}
        return {}


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    middle_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lang: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(
        "User", uselist=False, back_populates="profile", lazy="noload"
    )


class AuthProvider(Base):
    __tablename__ = "auth_providers"

    slug: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    enable: Mapped[bool] = mapped_column(Boolean, default=True)

    auths: Mapped[list["UserAuth"]] = relationship(
        "UserAuth", uselist=True, back_populates="provider", lazy="noload"
    )


class UserAuth(TimestampMixin, Base):
    __tablename__ = "user_auths"
    __table_args__ = (UniqueConstraint("user_id", "provider_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("auth_providers.id", ondelete="CASCADE"), index=True
    )

    subject: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # telegram_id, email, oauth сабы и т.д.
    token: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(
        "User", uselist=False, back_populates="auths", lazy="selectin"
    )

    provider: Mapped["AuthProvider"] = relationship(
        "AuthProvider", uselist=False, back_populates="auths", lazy="selectin"
    )


class AdminLoginRequest(Base):
    __tablename__ = "admin_login_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
