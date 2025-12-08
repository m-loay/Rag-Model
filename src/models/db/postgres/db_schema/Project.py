from .Base import SQLAlchemyBase
from sqlalchemy import DateTime, func, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .DataChunk import DataChunk
    from .Asset import Asset


class Project(SQLAlchemyBase):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    chunks: Mapped[List["DataChunk"]] = relationship(
        "DataChunk", back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (Index("ux_projects_project_id", project_id, unique=True),)
