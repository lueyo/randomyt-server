from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


def validate_date_format(date_str: str) -> str:
    """Valida que la fecha esté en formato dd/MM/YYYY"""
    pattern = r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\d{4}$"
    if not re.match(pattern, date_str):
        raise ValueError("Invalid date format. Expected dd/MM/YYYY")
    return date_str


class SearchDayQueryParamsDTO(BaseModel):
    """
    DTO para parámetros de búsqueda por día.

    Attributes:
        day: Día en formato dd/MM/YYYY (obligatorio)
        page: Número de página (default: 1, mínimo: 1)
        pageSize: Elementos por página (default: 30, mínimo: 1, máximo: 100)
        sort: Orden de clasificación (default: 'asc', valores: 'asc'|'desc')
    """

    day: str = Field(
        ...,
        description="Day to search in format dd/MM/YYYY",
        example="25/03/2023",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (starts at 1)",
        example=1,
    )
    pageSize: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (default 30, max 100)",
        example=30,
    )
    sort: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order: 'asc' for oldest first, 'desc' for newest first",
        example="asc",
    )

    @field_validator("day")
    @classmethod
    def validate_day_format(cls, v: str) -> str:
        """Validate that day is in dd/MM/YYYY format"""
        return validate_date_format(v)


class SearchIntervalQueryParamsDTO(BaseModel):
    """
    DTO para parámetros de búsqueda por intervalo de fechas.

    Attributes:
        startDay: Día de inicio en formato dd/MM/YYYY (default: 23/04/2005)
        endDay: Día de fin en formato dd/MM/YYYY (default: hoy)
        page: Número de página (default: 1, mínimo: 1)
        pageSize: Elementos por página (default: 30, mínimo: 1, máximo: 100)
        sort: Orden de clasificación (default: 'asc', valores: 'asc'|'desc')
    """

    startDay: str = Field(
        default="23/04/2005",
        description="Start day in format dd/MM/YYYY",
        example="23/04/2005",
    )
    endDay: Optional[str] = Field(
        default=None,
        description="End day in format dd/MM/YYYY (defaults to today if not provided)",
        example="25/03/2023",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (starts at 1)",
        example=1,
    )
    pageSize: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (default 30, max 100)",
        example=30,
    )
    sort: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order: 'asc' for oldest first, 'desc' for newest first",
        example="asc",
    )


class RandomByDayQueryParamsDTO(BaseModel):
    """
    DTO para parámetros de búsqueda de video aleatorio por día.

    Attributes:
        day: Día en formato dd/MM/YYYY (obligatorio)
    """

    day: str = Field(
        ...,
        description="Day to search in format dd/MM/YYYY",
        example="25/03/2023",
    )


class RandomByIntervalQueryParamsDTO(BaseModel):
    """
    DTO para parámetros de búsqueda de video aleatorio por intervalo de fechas.

    Attributes:
        startDay: Día de inicio en formato dd/MM/YYYY (default: 23/04/2005)
        endDay: Día de fin en formato dd/MM/YYYY (default: hoy)
    """

    startDay: str = Field(
        default="23/04/2005",
        description="Start day in format dd/MM/YYYY",
        example="23/04/2005",
    )
    endDay: Optional[str] = Field(
        default=None,
        description="End day in format dd/MM/YYYY (defaults to today if not provided)",
        example="25/03/2023",
    )
