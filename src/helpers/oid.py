from typing import Optional, Union
from bson import ObjectId
from bson.errors import InvalidId


def to_object_id(value: Union[str, ObjectId]) -> ObjectId:
    """Coerce str→ObjectId, pass through ObjectId, raise on invalid."""
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise ValueError("must be a valid ObjectId (24-char hex string)")
