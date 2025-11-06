from pydantic import BaseModel, Field, validator


class PublishVideoRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID")

    @validator("video_id")
    def validate_video_id(cls, v):
        if not v or len(v) != 11:
            raise ValueError("Video ID must be 11 characters long")
        allowed_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        )
        if not all(c in allowed_chars for c in v):
            raise ValueError("Video ID contains invalid characters")
        return v
