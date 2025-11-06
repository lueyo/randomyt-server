from motor.motor_asyncio import AsyncIOMotorClient
from common.config import DATABASE_URL

db_client = AsyncIOMotorClient(DATABASE_URL).get_database("randomyt_db")
