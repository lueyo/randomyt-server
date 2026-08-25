from typing import List, Optional, Tuple
from models.db.video_db_schema import VideoDB
from models.domain.video_model import VideoModel
from db.client import db_client
from abc import ABC, abstractmethod
from datetime import datetime
import json
import random as _random
from cachetools import TTLCache

_count_cache = TTLCache(maxsize=1024, ttl=45)
_total_count_cache = TTLCache(maxsize=8, ttl=10)
_video_cache = TTLCache(maxsize=4096, ttl=3600)


def _to_video_model(data: dict) -> VideoModel:
    video_db = VideoDB(**data)
    video_db_data = video_db.dict()
    if "_id" in video_db_data:
        video_db_data["id"] = video_db_data.pop("_id")
    return VideoModel(**video_db_data)


async def _count_with_cache(
    filter_query: dict, collation: Optional[dict] = None
) -> int:
    key = json.dumps(
        {"f": filter_query, "c": collation}, default=str, sort_keys=True
    )
    total = _count_cache.get(key)
    if total is None:
        if collation is not None:
            total = await db_client.videos.count_documents(
                filter_query, collation=collation
            )
        else:
            total = await db_client.videos.count_documents(filter_query)
        _count_cache[key] = total
    return total


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
        self, day: datetime, skip: int, limit: int, sort: str = "asc", isPostedDate: bool = False
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
        isPostedDate: bool = False,
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
        isPostedDate: bool = False,
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
        isPostedDate: bool = False,
    ) -> Tuple[List[VideoModel], int]:
        pass

    @abstractmethod
    async def get_random_video_by_interval_exclude_ids(
        self, start_day: datetime, end_day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        pass


class VideoRepository(IVideoRepository):

    async def _find_random(
        self,
        filter_query: Optional[dict] = None,
        date_field: Optional[str] = None,
    ) -> Optional[VideoModel]:
        if filter_query is None:
            filter_query = {}

        total = await db_client.videos.count_documents(filter_query)
        if total == 0:
            return None

        offset = _random.randint(0, total - 1)
        cursor = db_client.videos.find(filter_query)
        if date_field:
            cursor = cursor.sort(date_field, 1)
        cursor = cursor.skip(offset).limit(1)

        results = await cursor.to_list(1)
        if results:
            return _to_video_model(results[0])
        return None

    async def save_video(self, video_model: VideoModel) -> str:
        video_dict = video_model.dict()
        if "id" in video_dict:
            video_dict["_id"] = video_dict.pop("id")

        video_db = VideoDB(**video_dict)
        result = await db_client.videos.insert_one(video_db.dict(by_alias=True))
        return str(result.inserted_id)

    async def get_random_video(self) -> VideoModel:
        return await self._find_random()

    async def get_random_video_exclude_ids(self, exclude_ids: List[str]) -> VideoModel:
        if not exclude_ids:
            return await self._find_random()
        return await self._find_random({"_id": {"$nin": exclude_ids}})

    async def get_video_by_id(self, video_id: str) -> VideoModel:
        cached = _video_cache.get(video_id)
        if cached is not None:
            return cached

        video_data = await db_client.videos.find_one({"_id": video_id})
        if video_data:
            video_db = VideoDB(**video_data)
            video_db_data = video_db.dict()
            if "_id" in video_db_data:
                video_db_data["id"] = video_db_data.pop("_id")
            video = VideoModel(**video_db_data)
            _video_cache[video_id] = video
            return video
        else:
            return None

    async def count_videos(self) -> int:
        total = _total_count_cache.get("all")
        if total is None:
            total = await db_client.videos.count_documents({})
            _total_count_cache["all"] = total
        return total

    async def search_by_day(
        self, day: datetime, skip: int, limit: int, sort: str = "asc", isPostedDate: bool = False
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos subidos en un día específico.

        Args:
            day: Fecha del día a buscar (datetime con hora 00:00:00)
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)
            isPostedDate: Si True, busca por posted_date en vez de upload_date

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        # Calcular el rango del día (desde las 00:00:00 hasta las 23:59:59.999)
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)

        # Determinar el campo de fecha a usar
        date_field = "posted_date" if isPostedDate else "upload_date"

        # Determinar el orden de clasificación
        sort_order = 1 if sort == "asc" else -1

        # Contar total de documentos que coinciden
        total = await _count_with_cache(
            {date_field: {"$gte": start_of_day, "$lte": end_of_day}}
        )

        # Buscar documentos con paginación y orden cronológico
        cursor = (
            db_client.videos.find(
                {date_field: {"$gte": start_of_day, "$lte": end_of_day}}
            )
            .sort(date_field, sort_order)
            .skip(skip)
            .limit(limit)
        )

        results = await cursor.to_list(length=limit)
        return [_to_video_model(d) for d in results], total

    async def search_by_interval(
        self,
        start_day: datetime,
        end_day: datetime,
        skip: int,
        limit: int,
        sort: str = "asc",
        isPostedDate: bool = False,
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos subidos en un rango de fechas.

        Args:
            start_day: Fecha de inicio del rango
            end_day: Fecha de fin del rango
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)
            isPostedDate: Si True, busca por posted_date en vez de upload_date

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

        # Determinar el campo de fecha a usar
        date_field = "posted_date" if isPostedDate else "upload_date"

        # Determinar el orden de clasificación
        sort_order = 1 if sort == "asc" else -1

        # Contar total de documentos que coinciden
        total = await _count_with_cache(
            {date_field: {"$gte": start_of_start, "$lte": end_of_end}}
        )

        # Buscar documentos con paginación y orden cronológico
        cursor = (
            db_client.videos.find(
                {date_field: {"$gte": start_of_start, "$lte": end_of_end}}
            )
            .sort(date_field, sort_order)
            .skip(skip)
            .limit(limit)
        )

        results = await cursor.to_list(length=limit)
        return [_to_video_model(d) for d in results], total

    async def get_random_video_by_day(self, day: datetime) -> Optional[VideoModel]:
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
        return await self._find_random(
            {"upload_date": {"$gte": start_of_day, "$lte": end_of_day}},
            date_field="upload_date",
        )

    async def get_random_video_by_interval(
        self, start_day: datetime, end_day: datetime
    ) -> Optional[VideoModel]:
        start_of_start = datetime(
            start_day.year, start_day.month, start_day.day, 0, 0, 0
        )
        end_of_end = datetime(
            end_day.year, end_day.month, end_day.day, 23, 59, 59, 999999
        )
        return await self._find_random(
            {"upload_date": {"$gte": start_of_start, "$lte": end_of_end}},
            date_field="upload_date",
        )

    async def get_random_video_by_day_exclude_ids(
        self, day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
        filter_query: dict = {
            "upload_date": {"$gte": start_of_day, "$lte": end_of_day},
        }
        if exclude_ids:
            filter_query["_id"] = {"$nin": exclude_ids}
        return await self._find_random(filter_query, date_field="upload_date")

    async def search_by_title(
        self,
        query: str,
        tags: Optional[List[str]],
        skip: int,
        limit: int,
        sort: str = "asc",
        isPostedDate: bool = False,
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos por título y opcionalmente por tags.

        Args:
            query: Texto a buscar en el título (búsqueda parcial, case-insensitive y accent-insensitive)
            tags: Lista opcional de tags para filtrar (videos que tengan al menos uno de estos tags)
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)
            isPostedDate: Si True, ordena por posted_date en vez de upload_date

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        filter_query = {"title": {"$regex": query, "$options": "i"}}

        if tags and len(tags) > 0:
            filter_query["tags"] = {"$in": tags}

        # Determinar el campo de fecha para ordenar
        date_field = "posted_date" if isPostedDate else "upload_date"

        sort_order = 1 if sort == "asc" else -1

        # Collation configuration for accent-insensitive and case-insensitive search
        collation = {"locale": "es", "strength": 1}

        total = await _count_with_cache(filter_query, collation)

        cursor = (
            db_client.videos.find(filter_query, collation=collation)
            .sort(date_field, sort_order)
            .skip(skip)
            .limit(limit)
        )

        results = await cursor.to_list(length=limit)
        return [_to_video_model(d) for d in results], total

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
        isPostedDate: bool = False,
    ) -> Tuple[List[VideoModel], int]:
        """
        Busca videos combinando filtros de título, tags y fechas.

        Args:
            query: Texto opcional a buscar en el título (búsqueda parcial, case-insensitive y accent-insensitive)
            tags: Lista opcional de tags para filtrar (videos que tengan al menos uno de estos tags)
            day: Fecha específica opcional (datetime con hora 00:00:00)
            start_day: Fecha de inicio opcional del rango
            end_day: Fecha de fin opcional del rango
            skip: Número de documentos a omitir (para paginación)
            limit: Número máximo de documentos a devolver
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)
            isPostedDate: Si True, busca/ordena por posted_date en vez de upload_date

        Returns:
            Tupla con la lista de videos y el total de documentos encontrados
        """
        filter_query: dict = {}

        # Determinar el campo de fecha a usar
        date_field = "posted_date" if isPostedDate else "upload_date"

        if query and query.strip():
            filter_query["title"] = {"$regex": query, "$options": "i"}

        if tags and len(tags) > 0:
            filter_query["tags"] = {"$in": tags}

        if day:
            start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0)
            end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
            filter_query[date_field] = {"$gte": start_of_day, "$lte": end_of_day}
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
            filter_query[date_field] = {"$gte": start_of_start, "$lte": end_of_end}

        sort_order = 1 if sort == "asc" else -1

        # Collation configuration for accent-insensitive and case-insensitive search
        collation = {"locale": "es", "strength": 1}

        total = await _count_with_cache(filter_query, collation)

        cursor = (
            db_client.videos.find(filter_query, collation=collation)
            .sort(date_field, sort_order)
            .skip(skip)
            .limit(limit)
        )

        results = await cursor.to_list(length=limit)
        return [_to_video_model(d) for d in results], total

    async def get_random_video_by_interval_exclude_ids(
        self, start_day: datetime, end_day: datetime, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        start_of_start = datetime(
            start_day.year, start_day.month, start_day.day, 0, 0, 0
        )
        end_of_end = datetime(
            end_day.year, end_day.month, end_day.day, 23, 59, 59, 999999
        )
        filter_query: dict = {
            "upload_date": {"$gte": start_of_start, "$lte": end_of_end},
        }
        if exclude_ids:
            filter_query["_id"] = {"$nin": exclude_ids}
        return await self._find_random(filter_query, date_field="upload_date")
