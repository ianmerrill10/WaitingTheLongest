"""
===============================================================================
Unit Tests for Base Agent Module
===============================================================================
Tests for the base agent classes including AgentTask, AgentResult,
AgentMetrics, BaseAgent, and RateLimiter.

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
===============================================================================
"""

import pytest
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import queue

# Set up path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.base_agent import (
    AgentStatus,
    TaskPriority,
    AgentTask,
    AgentResult,
    AgentMetrics,
    BaseAgent,
    RateLimiter,
    generate_task_id
)


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.STARTING.value == "starting"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.PAUSED.value == "paused"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.STOPPED.value == "stopped"

    def test_status_count(self):
        """Test correct number of statuses."""
        assert len(AgentStatus) == 7


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_ordering(self):
        """Test priority values are ordered correctly."""
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value

    def test_priority_values(self):
        """Test specific priority values."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.CRITICAL.value == 4


class TestAgentTask:
    """Tests for AgentTask dataclass."""

    def test_task_creation_minimal(self):
        """Test creating task with minimal required fields."""
        task = AgentTask(
            task_id="test_123",
            task_type="test_task",
            payload={"key": "value"}
        )
        assert task.task_id == "test_123"
        assert task.task_type == "test_task"
        assert task.payload == {"key": "value"}
        assert task.priority == TaskPriority.NORMAL
        assert task.status == "pending"
        assert task.retries == 0

    def test_task_creation_full(self):
        """Test creating task with all fields."""
        now = datetime.now()
        task = AgentTask(
            task_id="test_456",
            task_type="complex_task",
            payload={"data": [1, 2, 3]},
            priority=TaskPriority.HIGH,
            created_at=now,
            status="running",
            max_retries=5
        )
        assert task.priority == TaskPriority.HIGH
        assert task.created_at == now
        assert task.status == "running"
        assert task.max_retries == 5

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = AgentTask(
            task_id="dict_test",
            task_type="serialization",
            payload={"test": True}
        )
        result = task.to_dict()

        assert isinstance(result, dict)
        assert result['task_id'] == "dict_test"
        assert result['task_type'] == "serialization"
        assert result['payload'] == {"test": True}
        assert result['priority'] == 2  # NORMAL value
        assert result['status'] == "pending"
        assert result['retries'] == 0

    def test_task_to_dict_with_dates(self):
        """Test datetime fields are serialized to ISO format."""
        now = datetime.now()
        task = AgentTask(
            task_id="date_test",
            task_type="dates",
            payload={},
            created_at=now,
            started_at=now
        )
        result = task.to_dict()

        assert result['created_at'] == now.isoformat()
        assert result['started_at'] == now.isoformat()


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_result_success(self):
        """Test creating a successful result."""
        result = AgentResult(
            success=True,
            message="Task completed successfully",
            items_processed=100
        )
        assert result.success is True
        assert result.message == "Task completed successfully"
        assert result.items_processed == 100
        assert result.errors == []

    def test_result_failure(self):
        """Test creating a failure result."""
        result = AgentResult(
            success=False,
            message="Task failed",
            errors=["Error 1", "Error 2"]
        )
        assert result.success is False
        assert len(result.errors) == 2

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = AgentResult(
            success=True,
            message="Done",
            items_processed=50,
            items_created=10,
            items_updated=40,
            duration_seconds=5.5
        )
        d = result.to_dict()

        assert d['success'] is True
        assert d['items_processed'] == 50
        assert d['items_created'] == 10
        assert d['items_updated'] == 40
        assert d['duration_seconds'] == 5.5


class TestAgentMetrics:
    """Tests for AgentMetrics dataclass."""

    def test_initial_metrics(self):
        """Test initial metrics values."""
        metrics = AgentMetrics()
        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 0
        assert metrics.success_rate == 100.0
        assert metrics.last_run is None

    def test_update_with_success(self):
        """Test updating metrics with successful result."""
        metrics = AgentMetrics()
        result = AgentResult(
            success=True,
            message="OK",
            items_processed=10,
            duration_seconds=2.0
        )

        metrics.update(result)

        assert metrics.tasks_completed == 1
        assert metrics.tasks_failed == 0
        assert metrics.total_items_processed == 10
        assert metrics.success_rate == 100.0
        assert metrics.last_run is not None

    def test_update_with_failure(self):
        """Test updating metrics with failed result."""
        metrics = AgentMetrics()
        result = AgentResult(success=False, message="Failed")

        metrics.update(result)

        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 1
        assert metrics.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate is calculated correctly."""
        metrics = AgentMetrics()

        # 3 successes
        for _ in range(3):
            metrics.update(AgentResult(success=True, message="OK"))

        # 1 failure
        metrics.update(AgentResult(success=False, message="Failed"))

        assert metrics.success_rate == 75.0  # 3/4 = 75%

    def test_avg_duration_calculation(self):
        """Test average duration is calculated correctly."""
        metrics = AgentMetrics()

        metrics.update(AgentResult(success=True, message="", duration_seconds=2.0))
        metrics.update(AgentResult(success=True, message="", duration_seconds=4.0))

        assert metrics.avg_task_duration == 3.0  # (2+4)/2 = 3


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    def __init__(self, agent_id="test_agent", **kwargs):
        # Mock database calls
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                super().__init__(
                    agent_id=agent_id,
                    agent_name="Test Agent",
                    agent_type="test",
                    **kwargs
                )

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a test task."""
        return AgentResult(
            success=True,
            message=f"Executed {task.task_type}",
            items_processed=1
        )

    async def run(self) -> AgentResult:
        """Run the test agent."""
        processed = 0
        while task := self.get_next_task():
            await self.execute_task(task)
            processed += 1
        return AgentResult(
            success=True,
            message="Run complete",
            items_processed=processed
        )


class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset registry before each test."""
        BaseAgent._registry.clear()
        # Clear message bus
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    def test_agent_initialization(self):
        """Test agent is properly initialized."""
        agent = ConcreteAgent(
            agent_id="init_test",
            description="Test description",
            config={"key": "value"}
        )

        assert agent.agent_id == "init_test"
        assert agent.agent_name == "Test Agent"
        assert agent.agent_type == "test"
        assert agent.description == "Test description"
        assert agent.config == {"key": "value"}
        assert agent.status == AgentStatus.IDLE

    def test_agent_registration(self):
        """Test agents are registered in global registry."""
        agent1 = ConcreteAgent(agent_id="agent1")
        agent2 = ConcreteAgent(agent_id="agent2")

        assert "agent1" in BaseAgent._registry
        assert "agent2" in BaseAgent._registry
        assert BaseAgent.get_agent("agent1") == agent1
        assert BaseAgent.get_agent("agent2") == agent2

    def test_add_and_get_task(self):
        """Test adding and retrieving tasks from queue."""
        agent = ConcreteAgent()

        task1 = AgentTask(
            task_id="task1",
            task_type="test",
            payload={},
            priority=TaskPriority.LOW
        )
        task2 = AgentTask(
            task_id="task2",
            task_type="test",
            payload={},
            priority=TaskPriority.HIGH
        )

        agent.add_task(task1)
        agent.add_task(task2)

        # Higher priority should come first
        retrieved = agent.get_next_task()
        assert retrieved.task_id == "task2"

        retrieved = agent.get_next_task()
        assert retrieved.task_id == "task1"

        # Queue should be empty now
        assert agent.get_next_task() is None

    def test_agent_messaging(self):
        """Test inter-agent messaging."""
        agent1 = ConcreteAgent(agent_id="sender")
        agent2 = ConcreteAgent(agent_id="receiver")

        agent1.send_message("receiver", {"data": "test"})

        messages = agent2.receive_messages()
        assert len(messages) == 1
        assert messages[0]['from'] == "sender"
        assert messages[0]['payload'] == {"data": "test"}

    def test_broadcast(self):
        """Test broadcasting to multiple agents."""
        agent1 = ConcreteAgent(agent_id="broadcaster")
        agent2 = ConcreteAgent(agent_id="receiver1")
        agent3 = ConcreteAgent(agent_id="receiver2")

        agent1.broadcast({"announcement": "hello"})

        msg2 = agent2.receive_messages()
        msg3 = agent3.receive_messages()

        assert len(msg2) == 1
        assert len(msg3) == 1

    def test_broadcast_by_type(self):
        """Test broadcasting to specific agent type."""
        agent1 = ConcreteAgent(agent_id="broadcaster")

        # Create agent of different type
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                agent2 = type('OtherAgent', (ConcreteAgent,), {})(agent_id="other")
                agent2.agent_type = "other_type"

        agent1.broadcast({"msg": "test"}, agent_type="other_type")

        messages = agent2.receive_messages()
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_agent_start(self):
        """Test starting an agent."""
        agent = ConcreteAgent()
        task = AgentTask(task_id="t1", task_type="test", payload={})
        agent.add_task(task)

        result = await agent.start()

        assert result.success is True
        assert agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Test error handling during agent run."""
        class FailingAgent(ConcreteAgent):
            async def run(self):
                raise ValueError("Test error")

        agent = FailingAgent(agent_id="failing")
        result = await agent.start()

        assert result.success is False
        assert agent.status == AgentStatus.ERROR
        assert "Test error" in result.errors[0]

    def test_stop_agent(self):
        """Test stopping an agent."""
        agent = ConcreteAgent()
        agent.stop()

        assert agent.status == AgentStatus.STOPPED

    def test_pause_resume(self):
        """Test pausing and resuming an agent."""
        agent = ConcreteAgent()
        agent.status = AgentStatus.RUNNING

        agent.pause()
        assert agent.status == AgentStatus.PAUSED

        agent.resume()
        assert agent.status == AgentStatus.RUNNING

    def test_get_status_report(self):
        """Test getting agent status report."""
        agent = ConcreteAgent()
        report = agent.get_status_report()

        assert 'agent_id' in report
        assert 'status' in report
        assert 'metrics' in report
        assert report['status'] == 'idle'

    def test_get_agents_by_type(self):
        """Test filtering agents by type."""
        agent1 = ConcreteAgent(agent_id="test1")
        agent2 = ConcreteAgent(agent_id="test2")

        agents = BaseAgent.get_agents_by_type("test")
        assert len(agents) == 2

    def test_get_all_agents(self):
        """Test getting all registered agents."""
        ConcreteAgent(agent_id="a1")
        ConcreteAgent(agent_id="a2")
        ConcreteAgent(agent_id="a3")

        all_agents = BaseAgent.get_all_agents()
        assert len(all_agents) == 3


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_creation(self):
        """Test creating rate limiter."""
        limiter = RateLimiter(calls_per_second=2.0)
        assert limiter.min_interval == 0.5  # 1/2 = 0.5 seconds

    @pytest.mark.asyncio
    async def test_rate_limiter_throttles(self):
        """Test rate limiter actually throttles calls."""
        limiter = RateLimiter(calls_per_second=100.0)  # Fast for testing

        start = datetime.now()
        await limiter.wait()
        await limiter.wait()
        elapsed = (datetime.now() - start).total_seconds()

        # Should have waited at least 0.01 seconds (1/100)
        assert elapsed >= 0.009  # Small margin for timing


class TestGenerateTaskId:
    """Tests for generate_task_id function."""

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = set()
        for _ in range(100):
            task_id = generate_task_id()
            assert task_id not in ids
            ids.add(task_id)

    def test_prefix_applied(self):
        """Test that prefix is applied correctly."""
        task_id = generate_task_id("custom_prefix")
        assert task_id.startswith("custom_prefix_")

    def test_default_prefix(self):
        """Test default prefix is 'task'."""
        task_id = generate_task_id()
        assert task_id.startswith("task_")

    def test_id_format(self):
        """Test ID has correct format."""
        task_id = generate_task_id("test")
        parts = task_id.split("_")
        assert len(parts) == 3  # prefix, timestamp, random
        assert len(parts[2]) == 8  # random part is 8 chars
