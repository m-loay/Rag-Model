from time import timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer
from typing import Optional, Dict, Any
from bson.objectid import ObjectId
import datetime as dt

class Asset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    asset_project_id: str = Field(..., min_length=1)
    asset_type: Optional[str] = Field(default=None, min_length=1) 
    asset_name: Optional[str] = Field(default=None, min_length=1)
    asset_size: Optional[int] = Field(default=None, ge=0)
    asset_config: Optional[Dict[str, Any]] = None
    asset_pushed_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    
    
    @field_serializer("id", "asset_project_id")
    def _ser_oid(self, v: ObjectId, _info):
        return str(v) if v is not None else None
    
    
    @field_validator("asset_type", "asset_name")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v
    
    
    @classmethod
    def get_indices(cls):
        return [
            {  # filter + sort efficiency
                "key": [("asset_project_id", 1)],
                "name": "asset_project_id_idx",
                "unique": False,
            },
            {  # useful compound index (adjust uniqueness as you need)
                "key": [("asset_project_id", 1), ("asset_name", 1)],
                "name": "asset_project_id_name_idx",
                "unique": False,
            },
        ]