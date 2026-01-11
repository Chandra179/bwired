import logging
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "research_tasks_queue"
        self.task_types = ["scout", "process", "discovery"]

    async def push_task(self, task_type: str, priority: float, payload: Dict[str, Any]) -> bool:
        """
        Push a task to the priority queue.

        Args:
            task_type: Type of task (scout, process, discovery)
            priority: Priority score (0.0 to 1.0, higher = more important)
            payload: Task data

        Returns:
            True if task was added successfully
        """
        raise NotImplementedError

    async def pop_task(self) -> Optional[Dict[str, Any]]:
        """
        Pop the highest priority task from the queue.

        Returns:
            Task data or None if queue is empty
        """
        raise NotImplementedError

    async def get_queue_size(self) -> int:
        """Get the number of tasks in the queue"""
        raise NotImplementedError

    async def clear_queue(self) -> bool:
        """Clear all tasks from the queue"""
        raise NotImplementedError