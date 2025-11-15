from typing import Optional, Any, Dict
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator
from helpers.oid import to_object_id

class DataChunk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: Optional[ObjectId] = Field(default=None, alias="_id")
    chunk_project_id: ObjectId
    chunk_asset_id: ObjectId
    chunk_order: int = Field(default=..., gt=0)
    chunk_text: str = Field(default=..., min_length=1)
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)


    @field_serializer("id", "chunk_project_id", "chunk_asset_id", when_used="json")
    def serialize_oid(self, v: ObjectId, _info):
        return str(v) if v is not None else None
    
    
    @field_validator("chunk_text")
    @classmethod
    def _nonempty_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("chunk_text must be non-empty")
        return v
    
    # Coerce both IDs before validation
    @field_validator("chunk_project_id", "chunk_asset_id", mode="before")
    @classmethod
    def _coerce_object_id(cls, v):
        return to_object_id(v)
    
    
    @classmethod
    def get_indices(cls):
        return [
            {
                "key":[
                    ("chunk_project_id", 1)
                ],
                "name": "chunk_project_id_index_1",
                "unique": False
            }
        ]