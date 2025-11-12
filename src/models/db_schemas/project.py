from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer
from typing import Optional
from bson.objectid import ObjectId

class Project(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    project_id: str = Field(..., min_length=1)
    
    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value:str) -> str:
        if not value.isalnum():
            raise ValueError("project_id must be alphanumeric")
        return value
    
    # So JSON responses won’t choke on ObjectId
    @field_serializer("id")
    def serialize_id(self, v: ObjectId, _info):
        return str(v) if v is not None else None