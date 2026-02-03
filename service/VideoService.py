from common.config import LIMIT_VIEWS
from common.utils.genid import gen_id
from common.utils.scriptscrapper import obtener_datos_youtube
from models.domain.video_model import VideoModel
from models.controller.input.publish_video_request import PublishVideoRequest
from models.controller.output.page_model import PageModel
from abc import ABC, abstractmethod
from repository.VideoRepository import VideoRepository
from datetime import datetime
from typing import List, Optional


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

    @abstractmethod
    async def count_videos(self) -> int:
        pass

    @abstractmethod
    async def search_by_day(
        self, day: str, page: int, pageSize: int, sort: str = "asc"
    ) -> PageModel:
        pass

    @abstractmethod
    async def search_by_interval(
        self, start_day: str, end_day: str, page: int, pageSize: int, sort: str = "asc"
    ) -> PageModel:
        pass

    @abstractmethod
    async def get_random_video_by_day(self, day: str) -> Optional[VideoModel]:
        pass

    @abstractmethod
    async def get_random_video_by_interval(
        self, start_day: str, end_day: str
    ) -> Optional[VideoModel]:
        pass

    @abstractmethod
    async def get_random_video_by_day_exclude_ids(
        self, day: str, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        pass

    @abstractmethod
    async def get_random_video_by_interval_exclude_ids(
        self, start_day: str, end_day: str, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
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
        if datos["views"] > LIMIT_VIEWS:
            raise ValueError("Video has more than LIMIT_VIEWS views")

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

    async def count_videos(self) -> int:
        return await self.video_repository.count_videos()

    async def search_by_day(
        self, day: str, page: int = 1, pageSize: int = 30, sort: str = "asc"
    ) -> PageModel:
        """
        Busca videos subidos en un día específico.

        Args:
            day: Fecha en formato dd/MM/YYYY
            page: Número de página (comienza en 1)
            pageSize: Número de elementos por página (default 30, max 100)
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)

        Returns:
            PageModel con los resultados paginados
        """
        # Validar pageSize máximo
        if pageSize > 100:
            pageSize = 100
        elif pageSize < 1:
            pageSize = 30

        # Validar sort
        if sort not in ["asc", "desc"]:
            sort = "asc"

        # Parsear la fecha del formato dd/MM/YYYY
        try:
            day_date = datetime.strptime(day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid date format. Expected dd/MM/YYYY")

        # Calcular skip para paginación
        skip = (page - 1) * pageSize

        # Buscar videos
        videos, total = await self.video_repository.search_by_day(
            day_date, skip, pageSize, sort
        )

        # Calcular páginas
        total_pages = (total + pageSize - 1) // pageSize if total > 0 else 0

        # Construir respuesta
        next_page: Optional[int] = page + 1 if page < total_pages else None
        previous_page: Optional[int] = page - 1 if page > 1 else None

        return PageModel(
            results=total,
            currentPage=page,
            pageSize=pageSize,
            nextPage=next_page,
            previousPage=previous_page,
        )

    async def search_by_interval(
        self,
        start_day: str,
        end_day: str,
        page: int = 1,
        pageSize: int = 30,
        sort: str = "asc",
    ) -> PageModel:
        """
        Busca videos subidos en un rango de fechas.

        Args:
            start_day: Fecha de inicio en formato dd/MM/YYYY (default: 23/04/2005)
            end_day: Fecha de fin en formato dd/MM/YYYY (default: fecha actual)
            page: Número de página (comienza en 1)
            pageSize: Número de elementos por página (default 30, max 100)
            sort: Orden de clasificación ("asc" para más antiguo primero, "desc" para más reciente primero)

        Returns:
            PageModel con los resultados paginados
        """
        # Validar pageSize máximo
        if pageSize > 100:
            pageSize = 100
        elif pageSize < 1:
            pageSize = 30

        # Validar sort
        if sort not in ["asc", "desc"]:
            sort = "asc"

        # Parsear las fechas del formato dd/MM/YYYY
        try:
            start_date = datetime.strptime(start_day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid start_day format. Expected dd/MM/YYYY")

        try:
            end_date = datetime.strptime(end_day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid end_day format. Expected dd/MM/YYYY")

        # Validar que start_day no sea mayor que end_day
        if start_date > end_date:
            raise ValueError("start_day cannot be greater than end_day")

        # Calcular skip para paginación
        skip = (page - 1) * pageSize

        # Buscar videos
        videos, total = await self.video_repository.search_by_interval(
            start_date, end_date, skip, pageSize, sort
        )

        # Calcular páginas
        total_pages = (total + pageSize - 1) // pageSize if total > 0 else 0

        # Construir respuesta
        next_page: Optional[int] = page + 1 if page < total_pages else None
        previous_page: Optional[int] = page - 1 if page > 1 else None

        return PageModel(
            results=total,
            currentPage=page,
            pageSize=pageSize,
            nextPage=next_page,
            previousPage=previous_page,
        )

    async def get_random_video_by_day(self, day: str) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un día específico.

        Args:
            day: Fecha en formato dd/MM/YYYY

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Parsear la fecha del formato dd/MM/YYYY
        try:
            day_date = datetime.strptime(day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid date format. Expected dd/MM/YYYY")

        return await self.video_repository.get_random_video_by_day(day_date)

    async def get_random_video_by_interval(
        self, start_day: str, end_day: str
    ) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un rango de fechas.

        Args:
            start_day: Fecha de inicio en formato dd/MM/YYYY
            end_day: Fecha de fin en formato dd/MM/YYYY

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Parsear las fechas del formato dd/MM/YYYY
        try:
            start_date = datetime.strptime(start_day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid start_day format. Expected dd/MM/YYYY")

        try:
            end_date = datetime.strptime(end_day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid end_day format. Expected dd/MM/YYYY")

        # Validar que start_day no sea mayor que end_day
        if start_date > end_date:
            raise ValueError("start_day cannot be greater than end_day")

        return await self.video_repository.get_random_video_by_interval(
            start_date, end_date
        )

    async def get_random_video_by_day_exclude_ids(
        self, day: str, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un día específico excluyendo IDs.

        Args:
            day: Fecha en formato dd/MM/YYYY
            exclude_ids: Lista de IDs a excluir

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Parsear la fecha del formato dd/MM/YYYY
        try:
            day_date = datetime.strptime(day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid date format. Expected dd/MM/YYYY")

        return await self.video_repository.get_random_video_by_day_exclude_ids(
            day_date, exclude_ids
        )

    async def get_random_video_by_interval_exclude_ids(
        self, start_day: str, end_day: str, exclude_ids: List[str]
    ) -> Optional[VideoModel]:
        """
        Obtiene un video aleatorio de un rango de fechas excluyendo IDs.

        Args:
            start_day: Fecha de inicio en formato dd/MM/YYYY
            end_day: Fecha de fin en formato dd/MM/YYYY
            exclude_ids: Lista de IDs a excluir

        Returns:
            VideoModel aleatorio o None si no hay videos
        """
        # Parsear las fechas del formato dd/MM/YYYY
        try:
            start_date = datetime.strptime(start_day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid start_day format. Expected dd/MM/YYYY")

        try:
            end_date = datetime.strptime(end_day, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid end_day format. Expected dd/MM/YYYY")

        # Validar que start_day no sea mayor que end_day
        if start_date > end_date:
            raise ValueError("start_day cannot be greater than end_day")

        return await self.video_repository.get_random_video_by_interval_exclude_ids(
            start_date, end_date, exclude_ids
        )
