from typing import Optional
from datetime import datetime
from db.client import db_tasks
from models.db.task_db_schema import TaskDB
from abc import ABC, abstractmethod
import uuid


class ITaskRepository(ABC):
    @abstractmethod
    async def insert_task(self, name: str) -> str:
        pass

    @abstractmethod
    async def get_next_pending_task(self) -> Optional[TaskDB]:
        pass

    @abstractmethod
    async def mark_task_completed(self, task_id: str) -> bool:
        pass

    @abstractmethod
    async def task_exists_by_name(self, name: str) -> bool:
        pass


class TaskRepository(ITaskRepository):
    async def insert_task(self, name: str) -> str:
        task_id = str(uuid.uuid4())
        task_dict = {
            "_id": task_id,
            "name": name,
            "date": datetime.now().isoformat(),
            "completed_at": None,
        }
        await db_tasks.tasks.insert_one(task_dict)
        return task_id

    async def get_next_pending_task(self) -> Optional[TaskDB]:
        task_data = await db_tasks.tasks.find_one(
            {"completed_at": None},
            sort=[("date", 1)]
        )
        if task_data:
            return TaskDB(**task_data)
        return None

    async def mark_task_completed(self, task_id: str) -> bool:
        result = await db_tasks.tasks.update_one(
            {"_id": task_id},
            {"$set": {"completed_at": datetime.now().isoformat()}}
        )
        return result.modified_count > 0

    async def task_exists_by_name(self, name: str) -> bool:
        count = await db_tasks.tasks.count_documents({"name": name})
        return count > 0
