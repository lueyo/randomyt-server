from repository.VideoRepository import IVideoRepository, VideoRepository
from fastapi import Depends
from service.VideoService import IVideoService, VideoService


_video_repository_instance = None
_video_service_instance = None


def get_video_repository() -> IVideoRepository:
    global _video_repository_instance
    if _video_repository_instance is None:
        _video_repository_instance = VideoRepository()
    return _video_repository_instance


def get_video_service(
    video_repository: IVideoRepository = Depends(get_video_repository),
) -> IVideoService:
    global _video_service_instance
    if _video_service_instance is None:
        _video_service_instance = VideoService(video_repository)
    return _video_service_instance
