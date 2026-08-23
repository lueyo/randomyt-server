from pymongo import ASCENDING
from db.client import db_client, db_tasks


async def ensure_indexes() -> None:
    await db_client.videos.create_index([("upload_date", ASCENDING)])
    await db_client.videos.create_index([("posted_date", ASCENDING)])
    await db_client.videos.create_index([("tags", ASCENDING)])
    await db_tasks.tasks.create_index(
        [("completed_at", ASCENDING), ("date", ASCENDING)]
    )
