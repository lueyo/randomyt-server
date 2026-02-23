from pydantic import BaseModel, Field
from typing import Optional, List

class MetaInfoDTO(BaseModel):
    author_name: str # titulo del video
    author_url: str # link completo de youtube https://youtu.be/{id}
    provider_name: str # 👁️ {views} 🗓️ {upload_date dd/MM/yyyy}
    provider_url: str # link completo de youtube https://youtu.be/{id}
    title: str = "Embed"
    type:str ="rich"
    version: str = "1.0"