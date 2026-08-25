import logging
import random
from pymongo import ASCENDING, UpdateOne
from pymongo.errors import OperationFailure
from db.client import db_client, db_tasks

logger = logging.getLogger(__name__)

_REDUNDANT_INDEXES = {
    "videos": [
        "upload_date_-1_autocreated",
        "_id_1_upload_date_1_autocreated",
    ],
}

_BATCH_SIZE = 10000


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


async def _backfill_random_field() -> None:
    collection = db_client.videos
    total = await collection.count_documents({"_r": {"$exists": False}})
    if total == 0:
        return

    logger.info("Backfilling _r field on %d documents...", total)
    cursor = collection.find(
        {"_r": {"$exists": False}}, {"_id": 1}
    ).batch_size(_BATCH_SIZE)

    ops = []
    async for doc in cursor:
        ops.append(
            UpdateOne({"_id": doc["_id"]}, {"$set": {"_r": random.random()}})
        )
        if len(ops) >= _BATCH_SIZE:
            await collection.bulk_write(ops, ordered=False)
            ops.clear()

    if ops:
        await collection.bulk_write(ops, ordered=False)

    logger.info("Backfill of _r field complete.")


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

    # Random field index for O(log N) random queries
    await db_client.videos.create_index([("_r", ASCENDING)])

    # --- tasks ---

    await db_tasks.tasks.create_index(
        [("completed_at", ASCENDING), ("date", ASCENDING)]
    )
    await db_tasks.tasks.create_index([("name", ASCENDING)])

    # Backfill _r on existing documents (runs once, skips already-set docs)
    await _backfill_random_field()
