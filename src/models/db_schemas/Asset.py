from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer
from typing import Optional, Dict, Any
from bson.objectid import ObjectId
import datetime as dt
from helpers.oid import to_object_id


class Asset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: Optional[ObjectId] = Field(default=None, alias="_id")
    asset_project_id: ObjectId
    asset_type: str = Field(default=..., min_length=1)
    asset_name: str = Field(default=..., min_length=1)
    asset_size: int = Field(default=..., ge=0)
    asset_config: Optional[Dict[str, Any]] = None
    asset_pushed_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    @field_serializer("id", "asset_project_id", when_used="json")
    def _ser_oid(self, v: ObjectId, _info):
        return str(v) if v is not None else None

    @field_validator("asset_type", "asset_name")
    @classmethod
    def nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be non-empty")
        return v

    # Coerce both IDs before validation
    @field_validator("id", "asset_project_id", mode="before")
    @classmethod
    def _coerce_object_id(cls, v):
        return to_object_id(v)

    @classmethod
    def get_indices(cls):
        return [
            {
                "key": [("asset_project_id", 1)],
                "name": "asset_project_id_idx",
                "unique": False,
            },
            {
                "key": [("asset_project_id", 1), ("asset_name", 1)],
                "name": "asset_project_id_name_idx",
                "unique": False,
            },
        ]
