# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Thread-safe task store for tracking async video processing jobs.
"""

import time
from enum import Enum
from threading import Lock
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Status of a video processing task"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    """Information about a video processing task"""
    task_id: str
    status: TaskStatus
    progress: float = 0.0  # 0.0 to 1.0
    current_frame: int = 0
    total_frames: int = 0
    message: Optional[str] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class TaskStore:
    """Thread-safe in-memory task store for tracking job status"""
    
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = Lock()
    
    def create_task(self, task_id: str) -> TaskInfo:
        """Create a new task with queued status"""
        with self._lock:
            task = TaskInfo(
                task_id=task_id,
                status=TaskStatus.QUEUED,
                message="Job queued for processing",
                created_at=time.time()
            )
            self._tasks[task_id] = task
            return task
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task info by ID"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs) -> Optional[TaskInfo]:
        """Update task fields"""
        with self._lock:
            if task_id not in self._tasks:
                return None
            
            task = self._tasks[task_id]
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            return task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the store"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """Get all tasks (for debugging)"""
        with self._lock:
            return dict(self._tasks)


# Global task store instance
task_store = TaskStore()
