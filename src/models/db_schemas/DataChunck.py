from typing import Optional, Any, Dict
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict, field_serializer

class DataChunk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: Optional[ObjectId] = Field(default=None, alias="_id")
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: Optional[ObjectId] = None

    @field_serializer("id", "chunk_project_id")
    def serialize_oid(self, v: ObjectId, _info):
        return str(v) if v is not None else None