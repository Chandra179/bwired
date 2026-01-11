import logging
import json
import uuid
from typing import Optional, Dict, Any
from ..storage.redis_client import RedisClient

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Redis-based priority queue for research tasks.
    
    Uses Redis sorted set (ZSET) data structure for efficient
    priority-based task scheduling. Higher priority tasks are
    processed first. This enables parallel processing with
    prioritization and depth-limited recursion.

    Task Types:
    - scout: Search for URLs given a research question
    - process: Crawl URL, extract facts, store results
    - discovery: Identify leads, score links, generate sub-questions

    Attributes:
        redis: Redis client instance
        queue_key: Redis key for the sorted set
        task_types: Valid task type identifiers

    Note:
        Priority scores range from 0.0 to 1.0, where 1.0 is highest priority.
        Redis ZADD stores members with scores, ZPOPMAX retrieves highest score.
    """
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.queue_key = "research_tasks_queue"
        self.task_types = ["scout", "process", "discovery"]

    async def push_task(self, task_type: str, priority: float, payload: Dict[str, Any]) -> bool:
        """
        Push a task to the priority queue.

        Tasks are stored as JSON in a Redis sorted set, with priority
        as the score. This ensures O(log N) insertion and O(1)
        retrieval of highest priority task.

        Args:
            task_type: Type of task (must be: scout, process, discovery)
            priority: Priority score (0.0 to 1.0, higher = more important)
            payload: Task-specific data (e.g., url, question, depth)

        Returns:
            True if task was added successfully, False otherwise

        Raises:
            ValueError: If task_type is invalid or priority out of range
        """
        if task_type not in self.task_types:
            raise ValueError(f"Invalid task_type: {task_type}. Must be one of {self.task_types}")
        
        if not 0.0 <= priority <= 1.0:
            raise ValueError(f"Priority must be between 0.0 and 1.0, got {priority}")

        task_id = str(uuid.uuid4())
        task_data = {
            "id": task_id,
            "type": task_type,
            "priority": priority,
            "payload": payload
        }
        
        member = json.dumps(task_data)
        result = await self.redis.zadd(self.queue_key, priority, member)
        
        if result > 0:
            logger.info(f"Pushed task {task_id} (type: {task_type}, priority: {priority})")
            return True
        return False

    async def pop_task(self) -> Optional[Dict[str, Any]]:
        """
        Pop the highest priority task from the queue.

        Uses Redis ZPOPMAX to atomically retrieve and remove the
        highest-priority task. This provides fair scheduling
        for parallel workers.

        Returns:
            Task data dictionary (id, type, priority, payload) or None if empty
        """
        result = await self.redis.zpopmax(self.queue_key)
        
        if result:
            member, score = result
            task_data = json.loads(member)
            logger.info(f"Popped task {task_data['id']} (type: {task_data['type']}, priority: {score})")
            return task_data
        
        return None

    async def get_queue_size(self) -> int:
        """
        Get the current number of tasks in the queue.

        Returns:
            Number of tasks waiting to be processed
        """
        return await self.redis.zcard(self.queue_key)

    async def clear_queue(self) -> bool:
        """
        Clear all tasks from the queue.

        Useful for resetting or cleanup operations.

        Returns:
            True if tasks were cleared, False if queue was already empty
        """
        result = await self.redis.remove_key(self.queue_key)
        if result > 0:
            logger.info("Cleared all tasks from queue")
            return True
        return False

    async def pop_by_type(self, task_type: str) -> Optional[Dict[str, Any]]:
        """
        Pop the highest priority task of a specific type.

        Iterates through queue to find and return the highest priority
        task matching the specified type. Non-matching tasks are
        temporarily removed and re-added to preserve priority order.

        Args:
            task_type: Type of task to pop (must be: scout, process, discovery)

        Returns:
            Task data dictionary or None if no matching task exists

        Raises:
            ValueError: If task_type is invalid

        Note:
            This is less efficient than pop_task() as it may require
            multiple ZPOPMAX/ZADD operations. Use pop_task() when
            type doesn't matter for better performance.
        """
        if task_type not in self.task_types:
            raise ValueError(f"Invalid task_type: {task_type}. Must be one of {self.task_types}")

        queue_size = await self.get_queue_size()
        if queue_size == 0:
            return None

        for _ in range(queue_size):
            temp_result = await self.redis.zpopmax(self.queue_key)
            if not temp_result:
                break
            
            member, score = temp_result
            task_data = json.loads(member)
            
            if task_data["type"] == task_type:
                logger.info(f"Popped {task_type} task {task_data['id']} (priority: {score})")
                return task_data
            else:
                # Re-add non-matching task to preserve its priority
                await self.redis.zadd(self.queue_key, score, member)
        
        return None
