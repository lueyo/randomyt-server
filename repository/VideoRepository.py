from models.db.video_db_schema import VideoDB
from models.domain.video_model import VideoModel
from db.client import db_client
from bson import ObjectId
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List


class IVideoRepository(ABC):
    @abstractmethod
    async def save_video(self, video_model: VideoModel) -> str:
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

    @abstractmethod
    async def count_videos(self) -> int:
        pass


class VideoRepository(IVideoRepository):

    async def save_video(self, video_model: VideoModel) -> str:
        video_dict = video_model.dict()
        if "id" in video_dict:
            video_dict["_id"] = video_dict.pop("id")

        video_db = VideoDB(**video_dict)
        result = await db_client.videos.insert_one(video_db.dict(by_alias=True))
        return str(result.inserted_id)

    async def get_random_video(self) -> VideoModel:
        pipeline = [{"$sample": {"size": 1}}]
        result = await db_client.videos.aggregate(pipeline).to_list(length=1)
        if result:
            video_data = result[0]
            video_db = VideoDB(**video_data)
            video_db_data = video_db.dict()
            if "_id" in video_db_data:
                video_db_data["id"] = video_db_data.pop("_id")
            return VideoModel(**video_db_data)
        else:
            return None

    async def get_random_video_exclude_ids(self, exclude_ids: List[str]) -> VideoModel:
        pipeline = [
            {"$match": {"_id": {"$nin": exclude_ids}}},
            {"$sample": {"size": 1}},
        ]
        result = await db_client.videos.aggregate(pipeline).to_list(length=1)
        if result:
            video_data = result[0]
            video_db = VideoDB(**video_data)
            video_db_data = video_db.dict()
            if "_id" in video_db_data:
                video_db_data["id"] = video_db_data.pop("_id")
            return VideoModel(**video_db_data)
        else:
            return None

    async def get_video_by_id(self, video_id: str) -> VideoModel:
        video_data = await db_client.videos.find_one({"_id": video_id})
        if video_data:
            video_db = VideoDB(**video_data)
            video_db_data = video_db.dict()
            if "_id" in video_db_data:
                video_db_data["id"] = video_db_data.pop("_id")
            return VideoModel(**video_db_data)
        else:
            return None

    async def count_videos(self) -> int:
        return await db_client.videos.count_documents({})
