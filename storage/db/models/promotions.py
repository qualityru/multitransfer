from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.db.models.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)

    promotions: Mapped[list["Promotion"]] = relationship(
        "Promotion",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("product_categories.id"), nullable=True
    )

    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cashback: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    category: Mapped[Optional[ProductCategory]] = relationship(
        "ProductCategory",
        back_populates="promotions",
    )
    details: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PromotionDetail(Base):
    __tablename__ = "promotion_details"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    info: Mapped[str] = mapped_column(String, nullable=True)
