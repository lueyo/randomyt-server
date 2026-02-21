from repository.VideoRepository import IVideoRepository, VideoRepository
from repository.TaskRepository import ITaskRepository, TaskRepository
from fastapi import Depends
from service.VideoService import IVideoService, VideoService
from service.TaskService import ITaskService, TaskService


_video_repository_instance = None
_video_service_instance = None
_task_repository_instance = None
_task_service_instance = None


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


def get_task_repository() -> ITaskRepository:
    global _task_repository_instance
    if _task_repository_instance is None:
        _task_repository_instance = TaskRepository()
    return _task_repository_instance


def get_task_service() -> ITaskService:
    global _task_repository_instance, _task_service_instance
    if _task_repository_instance is None:
        _task_repository_instance = TaskRepository()
    if _task_service_instance is None:
        _task_service_instance = TaskService(_task_repository_instance)
    return _task_service_instance
