"""
Waiting The Longest™ - Queue System
====================================
Background job queue with priority support.
"""

import asyncio
import heapq
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor
import threading


# =============================================================================
# Job Types
# =============================================================================

class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(int, Enum):
    """Job priority levels (lower number = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


# =============================================================================
# Job Definition
# =============================================================================

@dataclass(order=True)
class Job:
    """A queued job."""
    
    priority: int
    id: str = field(compare=False)
    name: str = field(compare=False)
    payload: dict = field(compare=False, default_factory=dict)
    status: JobStatus = field(compare=False, default=JobStatus.PENDING)
    created_at: datetime = field(compare=False, default_factory=datetime.utcnow)
    started_at: datetime | None = field(compare=False, default=None)
    completed_at: datetime | None = field(compare=False, default=None)
    result: Any = field(compare=False, default=None)
    error: str | None = field(compare=False, default=None)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    timeout: int = field(compare=False, default=300)  # seconds
    scheduled_at: datetime | None = field(compare=False, default=None)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def is_ready(self) -> bool:
        """Check if job is ready to run."""
        if self.status != JobStatus.PENDING:
            return False
        if self.scheduled_at and datetime.utcnow() < self.scheduled_at:
            return False
        return True
    
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


# =============================================================================
# Job Queue
# =============================================================================

class JobQueue:
    """
    Priority-based job queue with async support.
    """
    
    def __init__(self, max_workers: int = 4):
        self._queue: list[Job] = []
        self._jobs: dict[str, Job] = {}
        self._handlers: dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._running = False
        self._workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def register(self, job_name: str, handler: Callable):
        """Register a job handler."""
        self._handlers[job_name] = handler
    
    def enqueue(
        self,
        name: str,
        payload: dict | None = None,
        priority: JobPriority = JobPriority.NORMAL,
        delay: int = 0,
        max_retries: int = 3,
        timeout: int = 300,
    ) -> Job:
        """
        Add a job to the queue.
        
        Args:
            name: Job handler name
            payload: Job data
            priority: Job priority
            delay: Delay in seconds before job runs
            max_retries: Maximum retry attempts
            timeout: Job timeout in seconds
        
        Returns:
            The created job
        """
        scheduled_at = None
        if delay > 0:
            scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
        
        job = Job(
            id=str(uuid.uuid4()),
            name=name,
            priority=priority.value,
            payload=payload or {},
            max_retries=max_retries,
            timeout=timeout,
            scheduled_at=scheduled_at,
        )
        
        with self._lock:
            heapq.heappush(self._queue, job)
            self._jobs[job.id] = job
        
        return job
    
    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            return True
        return False
    
    def _get_next_job(self) -> Job | None:
        """Get next ready job from queue."""
        with self._lock:
            while self._queue:
                job = heapq.heappop(self._queue)
                
                if job.status == JobStatus.CANCELLED:
                    continue
                
                if not job.is_ready():
                    # Put back and wait
                    heapq.heappush(self._queue, job)
                    return None
                
                return job
        
        return None
    
    async def _execute_job(self, job: Job):
        """Execute a single job."""
        handler = self._handlers.get(job.name)
        
        if not handler:
            job.status = JobStatus.FAILED
            job.error = f"No handler registered for '{job.name}'"
            return
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**job.payload),
                    timeout=job.timeout,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        lambda: handler(**job.payload),
                    ),
                    timeout=job.timeout,
                )
            
            job.result = result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
        
        except asyncio.TimeoutError:
            job.error = "Job timed out"
            self._handle_job_failure(job)
        
        except Exception as e:
            job.error = str(e)
            self._handle_job_failure(job)
    
    def _handle_job_failure(self, job: Job):
        """Handle a failed job."""
        if job.can_retry():
            job.retry_count += 1
            job.status = JobStatus.PENDING
            
            # Exponential backoff
            delay = 2 ** job.retry_count
            job.scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
            
            with self._lock:
                heapq.heappush(self._queue, job)
        else:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
    
    async def process_one(self) -> bool:
        """Process one job from the queue."""
        job = self._get_next_job()
        if job:
            await self._execute_job(job)
            return True
        return False
    
    async def run(self):
        """Start processing jobs."""
        self._running = True
        
        while self._running:
            processed = await self.process_one()
            
            if not processed:
                # No jobs ready, wait a bit
                await asyncio.sleep(0.1)
    
    def stop(self):
        """Stop processing jobs."""
        self._running = False
    
    def stats(self) -> dict:
        """Get queue statistics."""
        with self._lock:
            pending = sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING)
            running = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
            completed = sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED)
            failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)
        
        return {
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "total": len(self._jobs),
        }


# =============================================================================
# Async Queue (Redis-like interface)
# =============================================================================

class AsyncQueue:
    """
    Async queue implementation for background processing.
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._queue: asyncio.Queue = asyncio.Queue()
        self._results: dict[str, Any] = {}
    
    async def put(self, item: Any, job_id: str | None = None) -> str:
        """Add item to queue."""
        job_id = job_id or str(uuid.uuid4())
        await self._queue.put((job_id, item))
        return job_id
    
    async def get(self, timeout: float | None = None) -> tuple[str, Any]:
        """Get item from queue."""
        if timeout:
            return await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout,
            )
        return await self._queue.get()
    
    async def set_result(self, job_id: str, result: Any):
        """Store job result."""
        self._results[job_id] = result
    
    async def get_result(
        self,
        job_id: str,
        timeout: float = 30,
    ) -> Any:
        """Get job result (blocks until available)."""
        start = time.time()
        while time.time() - start < timeout:
            if job_id in self._results:
                return self._results.pop(job_id)
            await asyncio.sleep(0.1)
        raise TimeoutError(f"Result for job {job_id} not available")
    
    def size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()


# =============================================================================
# Queue Worker
# =============================================================================

class QueueWorker:
    """
    Worker that processes jobs from a queue.
    """
    
    def __init__(
        self,
        queue: AsyncQueue,
        handler: Callable,
        concurrency: int = 1,
    ):
        self.queue = queue
        self.handler = handler
        self.concurrency = concurrency
        self._running = False
        self._tasks: list[asyncio.Task] = []
    
    async def _process(self):
        """Process jobs from queue."""
        while self._running:
            try:
                job_id, item = await self.queue.get(timeout=1.0)
                
                try:
                    if asyncio.iscoroutinefunction(self.handler):
                        result = await self.handler(item)
                    else:
                        result = self.handler(item)
                    
                    await self.queue.set_result(job_id, result)
                
                except Exception as e:
                    await self.queue.set_result(job_id, {"error": str(e)})
            
            except asyncio.TimeoutError:
                continue
    
    async def start(self):
        """Start worker."""
        self._running = True
        for _ in range(self.concurrency):
            task = asyncio.create_task(self._process())
            self._tasks.append(task)
    
    async def stop(self):
        """Stop worker."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks = []


# =============================================================================
# Predefined Jobs
# =============================================================================

# Job handlers registry
job_handlers: dict[str, Callable] = {}


def job(name: str):
    """Decorator to register a job handler."""
    def decorator(func: Callable):
        job_handlers[name] = func
        return func
    return decorator


@job("send_email")
async def send_email_job(to: str, subject: str, body: str, **kwargs):
    """Send email job."""
    # Implementation would use email service
    print(f"Sending email to {to}: {subject}")
    return {"sent": True, "to": to}


@job("process_adoption")
async def process_adoption_job(animal_id: int, adopter_email: str, **kwargs):
    """Process adoption job."""
    print(f"Processing adoption for animal {animal_id}")
    return {"processed": True, "animal_id": animal_id}


@job("sync_shelter")
async def sync_shelter_job(shelter_id: int, **kwargs):
    """Sync shelter data job."""
    print(f"Syncing shelter {shelter_id}")
    return {"synced": True, "shelter_id": shelter_id}


@job("generate_report")
async def generate_report_job(report_type: str, **kwargs):
    """Generate report job."""
    print(f"Generating {report_type} report")
    return {"generated": True, "report_type": report_type}


# =============================================================================
# Global Queue Instance
# =============================================================================

_job_queue: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """Get the global job queue."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
        # Register all handlers
        for name, handler in job_handlers.items():
            _job_queue.register(name, handler)
    return _job_queue


def enqueue(
    name: str,
    payload: dict | None = None,
    priority: JobPriority = JobPriority.NORMAL,
    **kwargs,
) -> Job:
    """Enqueue a job (convenience function)."""
    return get_job_queue().enqueue(name, payload, priority, **kwargs)
