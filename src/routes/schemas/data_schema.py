from pydantic import BaseModel
from typing import Optional


class ProcessRequest(BaseModel):
    file_id: Optional[str] = None
    chunk_size: int = 100
    overlap_size: int = 20
    do_reset: int = 0
