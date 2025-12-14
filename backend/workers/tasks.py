"""
Waiting The Longest™ - Background Tasks
=========================================
Celery-style background task utilities.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor
import threading
import queue


logger = logging.getLogger(__name__)


# =============================================================================
# Task Status
# =============================================================================

class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


@dataclass
class TaskResult:
    """Result of a task execution."""
    
    task_id: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    
    @property
    def duration_seconds(self) -> float | None:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "retries": self.retries,
        }


# =============================================================================
# Task Definition
# =============================================================================

@dataclass
class TaskDefinition:
    """Definition of a background task."""
    
    name: str
    func: Callable
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: float | None = None
    priority: int = 0
    
    # Execution tracking
    total_runs: int = 0
    total_failures: int = 0
    average_duration: float = 0.0


# =============================================================================
# Simple Task Queue
# =============================================================================

class SimpleTaskQueue:
    """
    Simple in-memory task queue for background processing.
    For production, use Celery, RQ, or similar.
    """
    
    def __init__(self, workers: int = 4):
        self.tasks: dict[str, TaskDefinition] = {}
        self.results: dict[str, TaskResult] = {}
        self.queue: queue.PriorityQueue = queue.PriorityQueue()
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self._running = False
        self._task_counter = 0
        self._lock = threading.Lock()
    
    def register(
        self,
        name: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        timeout: float | None = None,
        priority: int = 0,
    ):
        """
        Decorator to register a function as a task.
        
        Usage:
            @task_queue.register("send_email")
            def send_email(to: str, subject: str, body: str):
                ...
        """
        def decorator(func: Callable):
            task_name = name or func.__name__
            
            self.tasks[task_name] = TaskDefinition(
                name=task_name,
                func=func,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout,
                priority=priority,
            )
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            # Add delay method for async execution
            wrapper.delay = lambda *a, **kw: self.enqueue(task_name, *a, **kw)
            wrapper.apply_async = lambda *a, **kw: self.enqueue(task_name, *a, **kw)
            
            return wrapper
        
        return decorator
    
    def enqueue(
        self,
        task_name: str,
        *args,
        **kwargs,
    ) -> str:
        """Enqueue a task for execution."""
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")
        
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}_{int(time.time() * 1000)}"
        
        task_def = self.tasks[task_name]
        
        # Create result placeholder
        self.results[task_id] = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
        )
        
        # Add to queue (negative priority for correct ordering)
        self.queue.put((
            -task_def.priority,
            time.time(),
            task_id,
            task_name,
            args,
            kwargs,
        ))
        
        logger.info(f"Enqueued task: {task_name} (id={task_id})")
        
        return task_id
    
    def get_result(self, task_id: str) -> TaskResult | None:
        """Get the result of a task."""
        return self.results.get(task_id)
    
    def _execute_task(
        self,
        task_id: str,
        task_name: str,
        args: tuple,
        kwargs: dict,
        retry: int = 0,
    ):
        """Execute a task."""
        task_def = self.tasks[task_name]
        result = self.results[task_id]
        
        result.status = TaskStatus.RUNNING
        result.started_at = datetime.utcnow()
        result.retries = retry
        
        try:
            logger.info(f"Executing task: {task_name} (id={task_id}, retry={retry})")
            
            # Execute with timeout if specified
            output = task_def.func(*args, **kwargs)
            
            result.status = TaskStatus.COMPLETED
            result.result = output
            result.completed_at = datetime.utcnow()
            
            # Update stats
            task_def.total_runs += 1
            if result.duration_seconds:
                task_def.average_duration = (
                    (task_def.average_duration * (task_def.total_runs - 1) + result.duration_seconds)
                    / task_def.total_runs
                )
            
            logger.info(f"Task completed: {task_name} (id={task_id})")
            
        except Exception as e:
            logger.exception(f"Task failed: {task_name} (id={task_id})")
            
            if retry < task_def.max_retries:
                # Schedule retry
                result.status = TaskStatus.RETRY
                time.sleep(task_def.retry_delay)
                self._execute_task(task_id, task_name, args, kwargs, retry + 1)
            else:
                result.status = TaskStatus.FAILED
                result.error = str(e)
                result.completed_at = datetime.utcnow()
                task_def.total_failures += 1
    
    def start(self):
        """Start processing tasks."""
        if self._running:
            return
        
        self._running = True
        
        def worker():
            while self._running:
                try:
                    item = self.queue.get(timeout=1)
                    if item is None:
                        continue
                    
                    _, _, task_id, task_name, args, kwargs = item
                    self._execute_task(task_id, task_name, args, kwargs)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.exception(f"Worker error: {e}")
        
        # Start workers
        for _ in range(self.executor._max_workers):
            self.executor.submit(worker)
        
        logger.info("Task queue started")
    
    def stop(self):
        """Stop processing tasks."""
        self._running = False
        self.executor.shutdown(wait=True)
        logger.info("Task queue stopped")


# =============================================================================
# Async Task Queue
# =============================================================================

class AsyncTaskQueue:
    """
    Async task queue for coroutine-based tasks.
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.tasks: dict[str, TaskDefinition] = {}
        self.results: dict[str, TaskResult] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._task_counter = 0
    
    def register(
        self,
        name: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        timeout: float | None = None,
    ):
        """Register an async task."""
        def decorator(func: Callable[..., Awaitable]):
            task_name = name or func.__name__
            
            self.tasks[task_name] = TaskDefinition(
                name=task_name,
                func=func,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout,
            )
            
            return func
        
        return decorator
    
    async def enqueue(
        self,
        task_name: str,
        *args,
        **kwargs,
    ) -> str:
        """Enqueue an async task."""
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")
        
        self._task_counter += 1
        task_id = f"async_task_{self._task_counter}_{int(time.time() * 1000)}"
        
        self.results[task_id] = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
        )
        
        # Schedule task execution
        asyncio.create_task(
            self._execute_task(task_id, task_name, args, kwargs)
        )
        
        return task_id
    
    async def _execute_task(
        self,
        task_id: str,
        task_name: str,
        args: tuple,
        kwargs: dict,
        retry: int = 0,
    ):
        """Execute an async task."""
        async with self.semaphore:
            task_def = self.tasks[task_name]
            result = self.results[task_id]
            
            result.status = TaskStatus.RUNNING
            result.started_at = datetime.utcnow()
            result.retries = retry
            
            try:
                if task_def.timeout:
                    output = await asyncio.wait_for(
                        task_def.func(*args, **kwargs),
                        timeout=task_def.timeout,
                    )
                else:
                    output = await task_def.func(*args, **kwargs)
                
                result.status = TaskStatus.COMPLETED
                result.result = output
                result.completed_at = datetime.utcnow()
                
            except asyncio.TimeoutError:
                result.status = TaskStatus.FAILED
                result.error = "Task timed out"
                result.completed_at = datetime.utcnow()
                
            except Exception as e:
                if retry < task_def.max_retries:
                    await asyncio.sleep(task_def.retry_delay)
                    await self._execute_task(task_id, task_name, args, kwargs, retry + 1)
                else:
                    result.status = TaskStatus.FAILED
                    result.error = str(e)
                    result.completed_at = datetime.utcnow()


# =============================================================================
# Global Task Queue
# =============================================================================

_task_queue: SimpleTaskQueue | None = None


def get_task_queue() -> SimpleTaskQueue:
    """Get the global task queue."""
    global _task_queue
    if _task_queue is None:
        _task_queue = SimpleTaskQueue()
    return _task_queue


# =============================================================================
# Common Background Tasks
# =============================================================================

# Example task definitions (would be used with @task_queue.register decorator)

def send_email_task(to: str, subject: str, body: str) -> bool:
    """Send an email (background task)."""
    # Implementation would use SMTP
    logger.info(f"Sending email to {to}: {subject}")
    return True


def process_adoption_task(animal_id: int, adopter_email: str) -> dict:
    """Process an adoption (background task)."""
    logger.info(f"Processing adoption for animal {animal_id}")
    return {"success": True}


def sync_shelter_data_task(shelter_id: int) -> dict:
    """Sync data from shelter (background task)."""
    logger.info(f"Syncing shelter {shelter_id}")
    return {"animals_synced": 0}


def generate_report_task(report_type: str, params: dict) -> str:
    """Generate a report (background task)."""
    logger.info(f"Generating {report_type} report")
    return "report_url"
