from pydantic import BaseModel, Field
from typing import Optional


class PageModel(BaseModel):
    """
    Modelo de paginación para respuestas al frontend.

    Attributes:
        results: Cantidad total de resultados encontrados
        currentPage: Número de la página actual
        pageSize: Número de elementos por página (default 30, max 100)
        nextPage: Número de la siguiente página (solo se incluye si existe)
        previousPage: Número de la página anterior (solo se incluye si existe)
    """

    results: int = Field(..., description="Cantidad total de resultados")
    currentPage: int = Field(..., description="Número de la página actual")
    pageSize: int = Field(..., description="Número de elementos por página")
    nextPage: Optional[int] = Field(
        None, description="Número de la siguiente página (solo se incluye si existe)"
    )
    previousPage: Optional[int] = Field(
        None, description="Número de la página anterior (solo se incluye si existe)"
    )
