from typing import List, Optional, Tuple
from models.db.video_db_schema import VideoDB
from models.domain.video_model import VideoModel
from db.client import db_client
from bson import ObjectId
from abc import ABC, abstractmethod
from datetime import datetime


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
        self, day: datetime, skip: int, limit: int, sort: str = "asc"
    ) -> Tuple[List[VideoModel], int]:
        pass

    @abstractmethod
    async def search_by_interval(
        self,
        start_day: datetime,
        end_day: datetime,
        skip: int,
        limit: int,
        sort: str = "asc",
    ) -> Tuple[List[VideoModel], int]:
        pass

    @abstractmethod
    async def get_random_video_by_day(self, day: datetime) -> Optional[VideoModel]:
        pass

    @abstractmethod
    async def get_random_video_by_interval(
        self, start_day: datetime, end_day: datetime
    ) -> Optional[VideoModel]:
        pass

    @abstractmethod
    async def get_random_video_by_day_exclude_ids(
        self, day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        pass

    @abstractmethod
    async def search_by_title(
        self,
        query: str,
        tags: Optional[List[str]],
        skip: int,
        limit: int,
        sort: str = "asc",
    ) -> Tuple[List[VideoModel], int]:
        pass

    @abstractmethod
    async def search_combined(
        self,
        query: Optional[str],
        tags: Optional[List[str]],
        day: Optional[datetime],
        start_day: Optional[datetime],
        end_day: Optional[datetime],
        skip: int,
        limit: int,
        sort: str = "asc",
    ) -> Tuple[List[VideoModel], int]:
        pass

    @abstractmethod
    async def get_random_video_by_interval_exclude_ids(
        self, start_day: datetime, end_day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
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
        self, day: datetime, skip: int, limit: int, sort: str = "asc"
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos subidos en un día específico.

        Args:
            day: Fecha del día a buscar (datetime con hora 00:00:00)
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        # Calcular el rango del día (desde las 00:00:00 hasta las 23:59:59.999)
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)

        # Determinar el orden de clasificación
        sort_order = 1 if sort == "asc" else -1

        # Contar total de documentos que coinciden
        total = await db_client.videos.count_documents(
            {"upload_date": {"$gte": start_of_day, "$lte": end_of_day}}
        )

        # Buscar documentos con paginación y orden cronológico
        cursor = (
            db_client.videos.find(
                {"upload_date": {"$gte": start_of_day, "$lte": end_of_day}}
            )
            .sort("upload_date", sort_order)
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
        self,
        start_day: datetime,
        end_day: datetime,
        skip: int,
        limit: int,
        sort: str = "asc",
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos subidos en un rango de fechas.

        Args:
            start_day: Fecha de inicio del rango
            end_day: Fecha de fin del rango
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)

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

        # Determinar el orden de clasificación
        sort_order = 1 if sort == "asc" else -1

        # Contar total de documentos que coinciden
        total = await db_client.videos.count_documents(
            {"upload_date": {"$gte": start_of_start, "$lte": end_of_end}}
        )

        # Buscar documentos con paginación y orden cronológico
        cursor = (
            db_client.videos.find(
                {"upload_date": {"$gte": start_of_start, "$lte": end_of_end}}
            )
            .sort("upload_date", sort_order)
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

    async def get_random_video_by_day(self, day: datetime) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un día específico.

        Args:
            day: Fecha del día a buscar (datetime con hora 00:00:00)

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Calcular el rango del día (desde las 00:00:00 hasta las 23:59:59.999)
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)

        # Usar $sample para obtener un video aleatorio del día
        pipeline = [
            {"$match": {"upload_date": {"$gte": start_of_day, "$lte": end_of_day}}},
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

    async def get_random_video_by_interval(
        self, start_day: datetime, end_day: datetime
    ) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un rango de fechas.

        Args:
            start_day: Fecha de inicio del rango
            end_day: Fecha de fin del rango

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Normalizar las fechas para incluir todo el día
        start_of_start = datetime(
            start_day.year, start_day.month, start_day.day, 0, 0, 0
        )
        end_of_end = datetime(
            end_day.year, end_day.month, end_day.day, 23, 59, 59, 999999
        )

        # Usar $sample para obtener un video aleatorio del rango
        pipeline = [
            {"$match": {"upload_date": {"$gte": start_of_start, "$lte": end_of_end}}},
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

    async def get_random_video_by_day_exclude_ids(
        self, day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un día específico excluyendo IDs.

        Args:
            day: Fecha del día a buscar (datetime con hora 00:00:00)
            exclude_ids: Lista de IDs a excluir

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Calcular el rango del día (desde las 00:00:00 hasta las 23:59:59.999)
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)

        # Usar $sample para obtener un video aleatorio del día excluyendo IDs
        pipeline = [
            {
                "$match": {
                    "upload_date": {"$gte": start_of_day, "$lte": end_of_day},
                    "_id": {"$nin": exclude_ids},
                }
            },
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

    async def search_by_title(
        self,
        query: str,
        tags: Optional[List[str]],
        skip: int,
        limit: int,
        sort: str = "asc",
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos por título y opcionalmente por tags.

        Args:
            query: Texto a buscar en el título (búsqueda parcial, case-insensitive)
            tags: Lista opcional de tags para filtrar (videos que tengan al menos uno de estos tags)
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        filter_query = {"title": {"$regex": query, "$options": "i"}}

        if tags and len(tags) > 0:
            filter_query["tags"] = {"$in": tags}

        sort_order = 1 if sort == "asc" else -1

        total = await db_client.videos.count_documents(filter_query)

        cursor = (
            db_client.videos.find(filter_query)
            .sort("upload_date", sort_order)
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

    async def search_combined(
        self,
        query: Optional[str],
        tags: Optional[List[str]],
        day: Optional[datetime],
        start_day: Optional[datetime],
        end_day: Optional[datetime],
        skip: int,
        limit: int,
        sort: str = "asc",
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos combinando filtros de título, tags y fechas.

        Args:
            query: Texto opcional a buscar en el título (búsqueda parcial, case-insensitive)
            tags: Lista opcional de tags para filtrar (videos que tengan al menos uno de estos tags)
            day: Fecha específica opcional (datetime con hora 00:00:00)
            start_day: Fecha de inicio opcional del rango
            end_day: Fecha de fin opcional del rango
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        filter_query: dict = {}

        if query and query.strip():
            filter_query["title"] = {"$regex": query, "$options": "i"}

        if tags and len(tags) > 0:
            filter_query["tags"] = {"$in": tags}

        if day:
            start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
            end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
            filter_query["upload_date"] = {"$gte": start_of_day, "$lte": end_of_day}
        elif start_day or end_day:
            start_of_start = datetime(
                start_day.year if start_day else 2005, 4, 23, 0, 0, 0
            )
            end_of_end = datetime(
                end_day.year if end_day else datetime.now().year,
                end_day.month if end_day else datetime.now().month,
                end_day.day if end_day else datetime.now().day,
                23,
                59,
                59,
                999999,
            )
            filter_query["upload_date"] = {"$gte": start_of_start, "$lte": end_of_end}

        sort_order = 1 if sort == "asc" else -1

        total = await db_client.videos.count_documents(filter_query)

        cursor = (
            db_client.videos.find(filter_query)
            .sort("upload_date", sort_order)
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

    async def get_random_video_by_interval_exclude_ids(
        self, start_day: datetime, end_day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un rango de fechas excluyendo IDs.

        Args:
            start_day: Fecha de inicio del rango
            end_day: Fecha de fin del rango
            exclude_ids: Lista de IDs a excluir

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Normalizar las fechas para incluir todo el día
        start_of_start = datetime(
            start_day.year, start_day.month, start_day.day, 0, 0, 0
        )
        end_of_end = datetime(
            end_day.year, end_day.month, end_day.day, 23, 59, 59, 999999
        )

        # Usar $sample para obtener un video aleatorio del rango excluyendo IDs
        pipeline = [
            {
                "$match": {
                    "upload_date": {"$gte": start_of_start, "$lte": end_of_end},
                    "_id": {"$nin": exclude_ids},
                }
            },
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
