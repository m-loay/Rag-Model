from pydantic import BaseModel


class RetrivedfDocument(BaseModel):
    text: str
    score: float
