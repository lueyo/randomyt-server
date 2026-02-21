from pydantic import BaseModel


class TaskSearchRequest(BaseModel):
    search_term: str
