from pydantic import BaseModel, Field


class ArrayOfIDsRequest(BaseModel):
    ids: list[str] = Field(..., description="Lista de IDs de videos a excluir")
