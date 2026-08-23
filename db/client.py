from motor.motor_asyncio import AsyncIOMotorClient
from common.config import DATABASE_URL

_client = AsyncIOMotorClient(DATABASE_URL)
db_client = _client.get_database("randomyt_db")
db_tasks = _client.get_database("randomyt_cola")
