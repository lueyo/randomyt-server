from typing import List, Optional
from pydantic import BaseModel, Field

class TaskDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    date: str
    completed_at: Optional[str] = None



