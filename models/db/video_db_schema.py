from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

class VideoDB(BaseModel):
    id: str = Field(alias="_id")
    title: str
    posted_date: datetime # fecha de publicación en la base de datos
    upload_date: datetime # fecha de subida del video en YouTube
    tags: List[str]
    views: int



