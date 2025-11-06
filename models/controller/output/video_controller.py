from pydantic import BaseModel, Field
from datetime import datetime
from typing import List


class VideoSchema(BaseModel):
    id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    posted_date: datetime = Field(..., description="Date posted to database")
    upload_date: datetime = Field(..., description="Video upload date on YouTube")
    tags: List[str] = Field(default_factory=list, description="Video tags")
    views: int = Field(..., description="Number of views")
