from models.db.video_db_schema import VideoDB
from models.domain.video_model import VideoModel
from db.client import db_client
from bson import ObjectId
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Tuple


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

    @abstractmethod
    async def search_by_day(
        self, day: datetime, skip: int, limit: int
    ) -> Tuple[List[VideoModel], int]:
        pass

    @abstractmethod
    async def search_by_interval(
        self, start_day: datetime, end_day: datetime, skip: int, limit: int
    ) -> Tuple[List[VideoModel], int]:
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

    async def search_by_day(
        self, day: datetime, skip: int, limit: int
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos subidos en un día específico.

        Args:
            day: Fecha del día a buscar (datetime con hora 00:00:00)
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        # Calcular el rango del día (desde las 00:00:00 hasta las 23:59:59.999)
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)

        # Contar total de documentos que coinciden
        total = await db_client.videos.count_documents(
            {"upload_date": {"$gte": start_of_day, "$lte": end_of_day}}
        )

        # Buscar documentos con paginación y orden cronológico (más antiguo a más nuevo)
        cursor = (
            db_client.videos.find(
                {"upload_date": {"$gte": start_of_day, "$lte": end_of_day}}
            )
            .sort("upload_date", 1)
            .skip(skip)
            .limit(limit)
        )

        results = await cursor.to_list(length=limit)

        videos = []
        for video_data in results:
            video_db = VideoDB(**video_data)
            video_db_data = video_db.dict()
            if "_id" in video_db_data:
                video_db_data["id"] = video_db_data.pop("_id")
            videos.append(VideoModel(**video_db_data))

        return videos, total

    async def search_by_interval(
        self, start_day: datetime, end_day: datetime, skip: int, limit: int
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos subidos en un rango de fechas.

        Args:
            start_day: Fecha de inicio del rango
            end_day: Fecha de fin del rango
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        # Normalizar las fechas para incluir todo el día
        start_of_start = datetime(
            start_day.year, start_day.month, start_day.day, 0, 0, 0
        )
        end_of_end = datetime(
            end_day.year, end_day.month, end_day.day, 23, 59, 59, 999999
        )

        # Contar total de documentos que coinciden
        total = await db_client.videos.count_documents(
            {"upload_date": {"$gte": start_of_start, "$lte": end_of_end}}
        )

        # Buscar documentos con paginación y orden cronológico (más antiguo a más nuevo)
        cursor = (
            db_client.videos.find(
                {"upload_date": {"$gte": start_of_start, "$lte": end_of_end}}
            )
            .sort("upload_date", 1)
            .skip(skip)
            .limit(limit)
        )

        results = await cursor.to_list(length=limit)

        videos = []
        for video_data in results:
            video_db = VideoDB(**video_data)
            video_db_data = video_db.dict()
            if "_id" in video_db_data:
                video_db_data["id"] = video_db_data.pop("_id")
            videos.append(VideoModel(**video_db_data))

        return videos, total
