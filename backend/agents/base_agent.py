#!/usr/bin/env python3
"""
===============================================================================
Base Agent Class - Foundation for All AI Agents
===============================================================================
Provides common functionality for all agents in the Waiting The Longest system.

Features:
- Async task execution
- Progress tracking and reporting
- Database integration
- Logging and error handling
- Inter-agent communication
- Rate limiting
- State persistence

Author: Waiting The Longest Development Team
===============================================================================
"""

import os
import sys
import json
import logging
import asyncio
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading
import queue

# Add parent directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, init_db
from app.models import Shelter


class AgentStatus(Enum):
    """Agent lifecycle states"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentTask:
    """Represents a task to be executed by an agent"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'payload': self.payload,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'retries': self.retries
        }


@dataclass
class AgentResult:
    """Result of an agent operation"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_failed: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_items_processed: int = 0
    total_runtime_seconds: float = 0.0
    last_run: Optional[datetime] = None
    avg_task_duration: float = 0.0
    success_rate: float = 100.0

    def update(self, result: AgentResult):
        if result.success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        self.total_items_processed += result.items_processed
        self.total_runtime_seconds += result.duration_seconds
        self.last_run = datetime.now()

        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks > 0:
            self.success_rate = (self.tasks_completed / total_tasks) * 100
            self.avg_task_duration = self.total_runtime_seconds / total_tasks


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    Provides:
    - Task queue management
    - Database session handling
    - Logging infrastructure
    - Progress tracking
    - State persistence
    - Inter-agent messaging
    """

    # Class-level registry of all agent instances
    _registry: Dict[str, 'BaseAgent'] = {}
    _message_bus: queue.Queue = queue.Queue()

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.description = description
        self.config = config or {}

        self.status = AgentStatus.IDLE
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None

        # Task management
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.current_task: Optional[AgentTask] = None
        self.completed_tasks: List[AgentTask] = []

        # Metrics
        self.metrics = AgentMetrics()

        # State persistence
        self.state_dir = Path(__file__).parent / "state"
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / f"{agent_id}_state.json"

        # Logging
        self._setup_logging()

        # Register this agent
        BaseAgent._registry[agent_id] = self

        self.logger.info(f"Agent initialized: {agent_name} ({agent_id})")

    def _setup_logging(self):
        """Configure logging for this agent"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(f"agent.{self.agent_id}")
        self.logger.setLevel(logging.DEBUG)

        # File handler
        fh = logging.FileHandler(log_dir / f"{self.agent_id}.log")
        fh.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def get_db(self):
        """Get a database session"""
        return SessionLocal()

    def save_state(self):
        """Persist agent state to disk"""
        state = {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'status': self.status.value,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'metrics': {
                'tasks_completed': self.metrics.tasks_completed,
                'tasks_failed': self.metrics.tasks_failed,
                'total_items_processed': self.metrics.total_items_processed,
                'success_rate': self.metrics.success_rate
            },
            'completed_tasks': [t.to_dict() for t in self.completed_tasks[-100:]],  # Last 100
            'custom_state': self.get_custom_state()
        }

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self) -> Dict:
        """Load agent state from disk"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_custom_state(self) -> Dict:
        """Override to add custom state data"""
        return {}

    def set_custom_state(self, state: Dict):
        """Override to restore custom state data"""
        pass

    def add_task(self, task: AgentTask):
        """Add a task to the queue"""
        # Priority queue uses (priority, task) tuples, lower = higher priority
        priority = -task.priority.value  # Negate so higher priority comes first
        self.task_queue.put((priority, task))
        self.logger.debug(f"Task added: {task.task_id} ({task.task_type})")

    def get_next_task(self) -> Optional[AgentTask]:
        """Get the next task from the queue"""
        try:
            _, task = self.task_queue.get_nowait()
            return task
        except queue.Empty:
            return None

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a single task - must be implemented by subclasses"""
        pass

    @abstractmethod
    async def run(self) -> AgentResult:
        """Main agent execution loop - must be implemented by subclasses"""
        pass

    async def start(self):
        """Start the agent"""
        self.status = AgentStatus.STARTING
        self.started_at = datetime.now()
        self.logger.info(f"Starting agent: {self.agent_name}")

        try:
            self.status = AgentStatus.RUNNING
            result = await self.run()
            self.status = AgentStatus.COMPLETED
            self.metrics.update(result)
            self.save_state()
            return result
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Agent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"Agent failed: {str(e)}",
                errors=[str(e)]
            )

    def stop(self):
        """Stop the agent"""
        self.status = AgentStatus.STOPPED
        self.save_state()
        self.logger.info(f"Agent stopped: {self.agent_name}")

    def pause(self):
        """Pause the agent"""
        self.status = AgentStatus.PAUSED
        self.logger.info(f"Agent paused: {self.agent_name}")

    def resume(self):
        """Resume a paused agent"""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.RUNNING
            self.logger.info(f"Agent resumed: {self.agent_name}")

    def send_message(self, target_agent_id: str, message: Dict):
        """Send a message to another agent"""
        msg = {
            'from': self.agent_id,
            'to': target_agent_id,
            'timestamp': datetime.now().isoformat(),
            'payload': message
        }
        BaseAgent._message_bus.put(msg)
        self.logger.debug(f"Message sent to {target_agent_id}")

    def receive_messages(self) -> List[Dict]:
        """Receive messages intended for this agent"""
        messages = []
        temp_queue = queue.Queue()

        while not BaseAgent._message_bus.empty():
            try:
                msg = BaseAgent._message_bus.get_nowait()
                if msg['to'] == self.agent_id:
                    messages.append(msg)
                else:
                    temp_queue.put(msg)
            except queue.Empty:
                break

        # Put back messages for other agents
        while not temp_queue.empty():
            BaseAgent._message_bus.put(temp_queue.get())

        return messages

    def broadcast(self, message: Dict, agent_type: Optional[str] = None):
        """Broadcast a message to all agents (or agents of a specific type)"""
        for agent_id, agent in BaseAgent._registry.items():
            if agent_id != self.agent_id:
                if agent_type is None or agent.agent_type == agent_type:
                    self.send_message(agent_id, message)

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional['BaseAgent']:
        """Get an agent by ID from the registry"""
        return cls._registry.get(agent_id)

    @classmethod
    def get_agents_by_type(cls, agent_type: str) -> List['BaseAgent']:
        """Get all agents of a specific type"""
        return [a for a in cls._registry.values() if a.agent_type == agent_type]

    @classmethod
    def get_all_agents(cls) -> List['BaseAgent']:
        """Get all registered agents"""
        return list(cls._registry.values())

    def get_status_report(self) -> Dict:
        """Get a status report for this agent"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'agent_type': self.agent_type,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'queue_size': self.task_queue.qsize(),
            'metrics': {
                'tasks_completed': self.metrics.tasks_completed,
                'tasks_failed': self.metrics.tasks_failed,
                'success_rate': f"{self.metrics.success_rate:.1f}%",
                'total_items': self.metrics.total_items_processed,
                'avg_duration': f"{self.metrics.avg_task_duration:.2f}s"
            }
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.agent_id} ({self.status.value})>"


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, calls_per_second: float = 1.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self._lock = threading.Lock()

    async def wait(self):
        """Wait until the next call is allowed"""
        with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_call = asyncio.get_event_loop().time()


def generate_task_id(prefix: str = "task") -> str:
    """Generate a unique task ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
    return f"{prefix}_{timestamp}_{random_part}"


# Initialize database when module loads
try:
    init_db()
except Exception:
    pass  # Database might already be initialized
