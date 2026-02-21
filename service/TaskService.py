from abc import ABC, abstractmethod
from repository.TaskRepository import ITaskRepository
from models.db.task_db_schema import TaskDB
from typing import Optional


class ITaskService(ABC):
    @abstractmethod
    async def add_task(self, search_term: str) -> str:
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


class TaskService(ITaskService):
    def __init__(self, task_repository: ITaskRepository):
        self._task_repository = task_repository

    async def add_task(self, search_term: str) -> str:
        trimmed = search_term.strip()
        return await self._task_repository.insert_task(trimmed)

    async def get_next_pending_task(self) -> Optional[TaskDB]:
        return await self._task_repository.get_next_pending_task()

    async def mark_task_completed(self, task_id: str) -> bool:
        return await self._task_repository.mark_task_completed(task_id)

    async def task_exists_by_name(self, name: str) -> bool:
        return await self._task_repository.task_exists_by_name(name)
