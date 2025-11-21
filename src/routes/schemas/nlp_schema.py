from pydantic import BaseModel
from typing import Optional


class PushRequest(BaseModel):
    do_reset: int = 0


class SearchRequest(BaseModel):
    text: str
    limit: int = 5
