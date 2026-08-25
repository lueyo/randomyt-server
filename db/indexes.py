import logging
from pymongo import ASCENDING, TEXT
from pymongo.errors import OperationFailure
from db.client import db_client, db_tasks

logger = logging.getLogger(__name__)

_REDUNDANT_INDEXES = {
    "videos": [
        "upload_date_-1_autocreated",
        "_id_1_upload_date_1_autocreated",
    ],
}


async def _drop_redundant_indexes() -> None:
    for collection_name, index_names in _REDUNDANT_INDEXES.items():
        collection = db_client[collection_name]
        existing = await collection.index_information()
        for name in index_names:
            if name in existing:
                try:
                    await collection.drop_index(name)
                    logger.info("Dropped redundant index: %s.%s", collection_name, name)
                except OperationFailure as e:
                    logger.warning("Could not drop index %s.%s: %s", collection_name, name, e)


async def ensure_indexes() -> None:
    await _drop_redundant_indexes()

    # --- videos ---

    await db_client.videos.create_index([("upload_date", ASCENDING)])
    await db_client.videos.create_index([("posted_date", ASCENDING)])
    await db_client.videos.create_index([("tags", ASCENDING)])

    await db_client.videos.create_index(
        [("upload_date", ASCENDING), ("tags", ASCENDING)]
    )
    await db_client.videos.create_index(
        [("posted_date", ASCENDING), ("tags", ASCENDING)]
    )

    # --- tasks ---

    await db_tasks.tasks.create_index(
        [("completed_at", ASCENDING), ("date", ASCENDING)]
    )
    await db_tasks.tasks.create_index([("name", ASCENDING)])
