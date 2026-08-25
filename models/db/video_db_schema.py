from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

class VideoDB(BaseModel):
    id: str = Field(alias="_id")
    title: str
    posted_date: datetime
    upload_date: datetime
    tags: List[str]
    views: int



