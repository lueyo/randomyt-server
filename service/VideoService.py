from common.utils.genid import gen_id
from common.utils.scriptscrapper import obtener_datos_youtube
from models.domain.video_model import VideoModel
from models.controller.input.publish_video_request import PublishVideoRequest
from abc import ABC, abstractmethod
from repository.VideoRepository import VideoRepository
from datetime import datetime
from typing import List


class IVideoService(ABC):
    @abstractmethod
    async def publish_video(self, request: PublishVideoRequest) -> str:
        pass

    @abstractmethod
    async def get_random_video(self) -> VideoModel:
        pass

    @abstractmethod
    async def get_random_video_exclude_ids(self, exclude_ids: List[str]) -> VideoModel:
        pass

    @abstractmethod
    async def get_video_by_id(self, video_id: str) -> VideoModel:
        pass


class VideoService(IVideoService):

    def __init__(self, video_repository: VideoRepository):
        self.video_repository = video_repository

    async def publish_video(self, request: PublishVideoRequest) -> str:
        # Check if video already exists in database
        existing_video = await self.video_repository.get_video_by_id(request.video_id)
        if existing_video:
            raise ValueError("Video is in database")

        try:
            # Scrape data from YouTube
            datos = obtener_datos_youtube(request.video_id)
        except Exception:
            raise ValueError("Failed to retrieve video information")

        # Check views limit
        if datos["views"] > 2000:
            raise ValueError("Video has more than 2000 views")

        # Validate scraped data
        if not datos["titulo"] or not isinstance(datos["titulo"], str):
            raise ValueError("Invalid video data")

        video = VideoModel(
            id=request.video_id,
            title=datos["titulo"],
            posted_date=datetime.utcnow(),
            upload_date=datos["fecha_subida"],
            tags=datos["tags"],
            views=datos["views"],
        )
        try:
            return await self.video_repository.save_video(video)
        except Exception:
            raise ValueError("An error occurred while publishing the video")

    async def get_random_video(self) -> VideoModel:
        return await self.video_repository.get_random_video()

    async def get_random_video_exclude_ids(self, exclude_ids: List[str]) -> VideoModel:
        return await self.video_repository.get_random_video_exclude_ids(exclude_ids)

    async def get_video_by_id(self, video_id: str) -> VideoModel:
        return await self.video_repository.get_video_by_id(video_id)
