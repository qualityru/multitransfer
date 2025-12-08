from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from storage.db.models.base import Base


class GlobalSetting(Base):
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
