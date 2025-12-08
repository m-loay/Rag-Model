from .Base import SQLAlchemyBase
from sqlalchemy import ForeignKey, Index, Integer, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .DataChunk import DataChunk
    from .Project import Project


class Asset(SQLAlchemyBase):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    asset_name: Mapped[str] = mapped_column(String, nullable=False)
    asset_size: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    asset_project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    chunks: Mapped[List["DataChunk"]] = relationship(
        "DataChunk", back_populates="asset", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_asset_project_id", asset_project_id),
        Index("ix_asset_type", asset_type),
        Index("ix_asset_project_name", asset_project_id, asset_name),
    )
