from common.config import LIMIT_VIEWS
from common.utils.youtube_video_id_validator import validate_youtube_video_id
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List


class VideoModel(BaseModel):
    id: str  # este es el ID de YouTube que identifica el video y se lo pasa el cliente, los demás datos se obtienen de YouTube con scrapping excepto posted_date
    title: str = Field(..., description="Título del video")
    posted_date: datetime = Field(
        ..., description="Fecha de publicación del video en la base de datos"
    )
    upload_date: datetime = Field(..., description="Fecha de subida del video")
    tags: List[str] = Field(default_factory=list)
    views: int = Field(
        ...,
        le=LIMIT_VIEWS,
        description="Número de visualizaciones del video, no puede ser superior a 2000",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v):
        if not validate_youtube_video_id(v):
            raise ValueError("Invalid YouTube video ID")
        return v
