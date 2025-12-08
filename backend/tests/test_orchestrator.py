"""
===============================================================================
Unit Tests for Agent Orchestrator Module
===============================================================================
Tests for the orchestrator module including OrchestratorMode, AgentGroup,
AgentRegistration, ScheduledTask, AgentOrchestrator, and get_orchestrator.

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
===============================================================================
"""

import pytest
import asyncio
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, call
from pathlib import Path

# Set up path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.orchestrator import (
    OrchestratorMode,
    AgentGroup,
    AgentRegistration,
    ScheduledTask,
    AgentOrchestrator,
    get_orchestrator
)
from agents.base_agent import (
    AgentStatus,
    TaskPriority,
    AgentTask,
    AgentResult,
    BaseAgent
)


class TestOrchestratorMode:
    """Tests for OrchestratorMode enum."""

    def test_mode_values(self):
        """Test all mode values exist."""
        assert OrchestratorMode.IDLE.value == "idle"
        assert OrchestratorMode.DISCOVERY.value == "discovery"
        assert OrchestratorMode.MAINTENANCE.value == "maintenance"
        assert OrchestratorMode.MARKETING.value == "marketing"
        assert OrchestratorMode.FULL.value == "full"
        assert OrchestratorMode.EMERGENCY.value == "emergency"

    def test_mode_count(self):
        """Test correct number of modes."""
        assert len(OrchestratorMode) == 6

    def test_mode_comparison(self):
        """Test mode enum values can be compared."""
        assert OrchestratorMode.IDLE == OrchestratorMode.IDLE
        assert OrchestratorMode.IDLE != OrchestratorMode.DISCOVERY


class TestAgentGroup:
    """Tests for AgentGroup enum."""

    def test_group_values(self):
        """Test all group values exist."""
        assert AgentGroup.STATE.value == "state"
        assert AgentGroup.SOCIAL_MEDIA.value == "social_media"
        assert AgentGroup.DATA_PROCESSING.value == "data_processing"
        assert AgentGroup.MARKETING.value == "marketing"
        assert AgentGroup.OPERATIONS.value == "operations"
        assert AgentGroup.MONITORING.value == "monitoring"

    def test_group_count(self):
        """Test correct number of groups."""
        assert len(AgentGroup) == 6

    def test_group_comparison(self):
        """Test group enum values can be compared."""
        assert AgentGroup.STATE == AgentGroup.STATE
        assert AgentGroup.STATE != AgentGroup.MARKETING


class TestAgentRegistration:
    """Tests for AgentRegistration dataclass."""

    def test_registration_creation_minimal(self):
        """Test creating registration with minimal required fields."""
        reg = AgentRegistration(
            agent_id="test_agent",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.STATE
        )
        assert reg.agent_id == "test_agent"
        assert reg.agent_type == "test"
        assert reg.agent_class == "TestAgent"
        assert reg.group == AgentGroup.STATE
        assert reg.priority == 5
        assert reg.max_concurrent == 1
        assert reg.cooldown_minutes == 30
        assert reg.last_run is None
        assert reg.is_running is False
        assert reg.enabled is True
        assert reg.config == {}

    def test_registration_creation_full(self):
        """Test creating registration with all fields."""
        now = datetime.now()
        reg = AgentRegistration(
            agent_id="full_agent",
            agent_type="specialized",
            agent_class="FullAgent",
            group=AgentGroup.MARKETING,
            priority=10,
            max_concurrent=5,
            cooldown_minutes=120,
            last_run=now,
            is_running=True,
            enabled=False,
            config={"key": "value"}
        )
        assert reg.agent_id == "full_agent"
        assert reg.priority == 10
        assert reg.max_concurrent == 5
        assert reg.cooldown_minutes == 120
        assert reg.last_run == now
        assert reg.is_running is True
        assert reg.enabled is False
        assert reg.config == {"key": "value"}

    def test_registration_fields_mutable(self):
        """Test registration fields can be modified."""
        reg = AgentRegistration(
            agent_id="mutable_test",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.STATE
        )

        reg.enabled = False
        assert reg.enabled is False

        reg.is_running = True
        assert reg.is_running is True

        now = datetime.now()
        reg.last_run = now
        assert reg.last_run == now


class TestScheduledTask:
    """Tests for ScheduledTask dataclass."""

    def test_scheduled_task_minimal(self):
        """Test creating scheduled task with minimal fields."""
        schedule_time = datetime.now() + timedelta(hours=1)
        task = ScheduledTask(
            task_id="scheduled_123",
            agent_id="test_agent",
            task_type="test_task",
            schedule_time=schedule_time
        )
        assert task.task_id == "scheduled_123"
        assert task.agent_id == "test_agent"
        assert task.task_type == "test_task"
        assert task.schedule_time == schedule_time
        assert task.recurrence is None
        assert task.payload == {}
        assert task.priority == TaskPriority.NORMAL
        assert isinstance(task.created_at, datetime)

    def test_scheduled_task_full(self):
        """Test creating scheduled task with all fields."""
        schedule_time = datetime.now() + timedelta(hours=2)
        created_time = datetime.now()
        task = ScheduledTask(
            task_id="scheduled_456",
            agent_id="recurring_agent",
            task_type="recurring_task",
            schedule_time=schedule_time,
            recurrence="daily",
            payload={"data": "test"},
            priority=TaskPriority.HIGH,
            created_at=created_time
        )
        assert task.recurrence == "daily"
        assert task.payload == {"data": "test"}
        assert task.priority == TaskPriority.HIGH
        assert task.created_at == created_time

    def test_scheduled_task_recurrence_values(self):
        """Test different recurrence values."""
        schedule_time = datetime.now()

        for recurrence in ["hourly", "daily", "weekly", None]:
            task = ScheduledTask(
                task_id=f"task_{recurrence}",
                agent_id="agent",
                task_type="test",
                schedule_time=schedule_time,
                recurrence=recurrence
            )
            assert task.recurrence == recurrence


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset singleton instance and registry before each test."""
        # Reset singleton
        AgentOrchestrator._instance = None

        # Clear base agent registry
        BaseAgent._registry.clear()

        yield

        # Cleanup after test
        AgentOrchestrator._instance = None
        BaseAgent._registry.clear()

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance with mocked dependencies."""
        with patch('agents.orchestrator.get_all_state_agents'):
            with patch('agents.orchestrator.get_state_agent'):
                with patch('agents.base_agent.init_db'):
                    with patch('agents.base_agent.SessionLocal'):
                        orch = AgentOrchestrator()
                        return orch

    def test_singleton_pattern(self):
        """Test orchestrator implements singleton pattern."""
        with patch('agents.orchestrator.get_all_state_agents'):
            with patch('agents.orchestrator.get_state_agent'):
                with patch('agents.base_agent.init_db'):
                    with patch('agents.base_agent.SessionLocal'):
                        orch1 = AgentOrchestrator()
                        orch2 = AgentOrchestrator()
                        orch3 = get_orchestrator()

                        assert orch1 is orch2
                        assert orch2 is orch3
                        assert id(orch1) == id(orch2) == id(orch3)

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator is properly initialized."""
        assert orchestrator.agent_id == "orchestrator"
        assert orchestrator.agent_name == "Agent Orchestrator"
        assert orchestrator.agent_type == "orchestrator"
        assert orchestrator.mode == OrchestratorMode.IDLE
        assert isinstance(orchestrator.agent_registry, dict)
        assert isinstance(orchestrator.active_agents, dict)
        assert isinstance(orchestrator.scheduled_tasks, list)
        assert isinstance(orchestrator.task_history, list)
        assert 'agents_registered' in orchestrator.stats
        assert 'tasks_scheduled' in orchestrator.stats
        assert 'tasks_completed' in orchestrator.stats
        assert 'tasks_failed' in orchestrator.stats

    def test_orchestrator_registers_agents(self, orchestrator):
        """Test orchestrator registers agents on initialization."""
        # Should have state agents and specialized agents
        assert len(orchestrator.agent_registry) > 0
        assert orchestrator.stats['agents_registered'] > 0

        # Check for some state agents
        state_agent_ids = [
            f"state_{code.lower()}"
            for code in ['NY', 'CA', 'TX', 'FL']
        ]
        for agent_id in state_agent_ids:
            assert agent_id in orchestrator.agent_registry

    def test_register_agent(self, orchestrator):
        """Test registering a new agent."""
        initial_count = len(orchestrator.agent_registry)

        reg = AgentRegistration(
            agent_id="new_test_agent",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            priority=8
        )

        orchestrator.register_agent(reg)

        assert len(orchestrator.agent_registry) == initial_count + 1
        assert "new_test_agent" in orchestrator.agent_registry
        assert orchestrator.agent_registry["new_test_agent"] == reg

    def test_unregister_agent(self, orchestrator):
        """Test unregistering an agent."""
        # Register a test agent
        reg = AgentRegistration(
            agent_id="temp_agent",
            agent_type="test",
            agent_class="TempAgent",
            group=AgentGroup.OPERATIONS
        )
        orchestrator.register_agent(reg)
        assert "temp_agent" in orchestrator.agent_registry

        # Unregister it
        orchestrator.unregister_agent("temp_agent")
        assert "temp_agent" not in orchestrator.agent_registry

    def test_unregister_nonexistent_agent(self, orchestrator):
        """Test unregistering an agent that doesn't exist."""
        # Should not raise error
        orchestrator.unregister_agent("nonexistent_agent")

    def test_enable_agent(self, orchestrator):
        """Test enabling an agent."""
        # Register a disabled agent
        reg = AgentRegistration(
            agent_id="disabled_agent",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            enabled=False
        )
        orchestrator.register_agent(reg)
        assert orchestrator.agent_registry["disabled_agent"].enabled is False

        # Enable it
        orchestrator.enable_agent("disabled_agent")
        assert orchestrator.agent_registry["disabled_agent"].enabled is True

    def test_disable_agent(self, orchestrator):
        """Test disabling an agent."""
        # Register an enabled agent
        reg = AgentRegistration(
            agent_id="enabled_agent",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            enabled=True
        )
        orchestrator.register_agent(reg)
        assert orchestrator.agent_registry["enabled_agent"].enabled is True

        # Disable it
        orchestrator.disable_agent("enabled_agent")
        assert orchestrator.agent_registry["enabled_agent"].enabled is False

    def test_enable_disable_nonexistent_agent(self, orchestrator):
        """Test enabling/disabling nonexistent agent doesn't error."""
        orchestrator.enable_agent("nonexistent")
        orchestrator.disable_agent("nonexistent")
        # Should not raise error

    def test_schedule_task(self, orchestrator):
        """Test scheduling a task."""
        initial_count = len(orchestrator.scheduled_tasks)
        initial_stats = orchestrator.stats['tasks_scheduled']

        schedule_time = datetime.now() + timedelta(hours=1)
        task = ScheduledTask(
            task_id="scheduled_test",
            agent_id="test_agent",
            task_type="test_task",
            schedule_time=schedule_time
        )

        orchestrator.schedule_task(task)

        assert len(orchestrator.scheduled_tasks) == initial_count + 1
        assert orchestrator.stats['tasks_scheduled'] == initial_stats + 1
        assert task in orchestrator.scheduled_tasks

    def test_schedule_task_ordering(self, orchestrator):
        """Test scheduled tasks are ordered by time."""
        now = datetime.now()

        task1 = ScheduledTask(
            task_id="task1",
            agent_id="agent",
            task_type="test",
            schedule_time=now + timedelta(hours=3)
        )
        task2 = ScheduledTask(
            task_id="task2",
            agent_id="agent",
            task_type="test",
            schedule_time=now + timedelta(hours=1)
        )
        task3 = ScheduledTask(
            task_id="task3",
            agent_id="agent",
            task_type="test",
            schedule_time=now + timedelta(hours=2)
        )

        orchestrator.schedule_task(task1)
        orchestrator.schedule_task(task2)
        orchestrator.schedule_task(task3)

        # Should be sorted by schedule_time
        assert orchestrator.scheduled_tasks[0].task_id == "task2"
        assert orchestrator.scheduled_tasks[1].task_id == "task3"
        assert orchestrator.scheduled_tasks[2].task_id == "task1"

    def test_cancel_scheduled_task(self, orchestrator):
        """Test cancelling a scheduled task."""
        task = ScheduledTask(
            task_id="cancel_me",
            agent_id="agent",
            task_type="test",
            schedule_time=datetime.now() + timedelta(hours=1)
        )
        orchestrator.schedule_task(task)
        assert task in orchestrator.scheduled_tasks

        orchestrator.cancel_scheduled_task("cancel_me")
        assert task not in orchestrator.scheduled_tasks

    def test_cancel_nonexistent_task(self, orchestrator):
        """Test cancelling a task that doesn't exist."""
        # Should not raise error
        orchestrator.cancel_scheduled_task("nonexistent_task")

    @pytest.mark.asyncio
    async def test_start_agent_unknown(self, orchestrator):
        """Test starting an unknown agent returns None."""
        result = await orchestrator.start_agent("unknown_agent")
        assert result is None

    @pytest.mark.asyncio
    async def test_start_agent_disabled(self, orchestrator):
        """Test starting a disabled agent returns None."""
        reg = AgentRegistration(
            agent_id="disabled_test",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            enabled=False
        )
        orchestrator.register_agent(reg)

        result = await orchestrator.start_agent("disabled_test")
        assert result is None

    @pytest.mark.asyncio
    async def test_start_agent_already_running(self, orchestrator):
        """Test starting an already running agent returns None."""
        reg = AgentRegistration(
            agent_id="running_test",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            is_running=True
        )
        orchestrator.register_agent(reg)

        result = await orchestrator.start_agent("running_test")
        assert result is None

    @pytest.mark.asyncio
    async def test_start_agent_cooldown(self, orchestrator):
        """Test starting an agent in cooldown returns None."""
        reg = AgentRegistration(
            agent_id="cooldown_test",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            last_run=datetime.now() - timedelta(minutes=15),
            cooldown_minutes=30
        )
        orchestrator.register_agent(reg)

        result = await orchestrator.start_agent("cooldown_test")
        assert result is None

    @pytest.mark.asyncio
    async def test_start_agent_cooldown_expired(self, orchestrator):
        """Test starting an agent after cooldown succeeds."""
        # Mock agent creation to return None (unimplemented agent)
        with patch.object(orchestrator, '_create_agent', return_value=None):
            reg = AgentRegistration(
                agent_id="cooldown_expired_test",
                agent_type="test",
                agent_class="TestAgent",
                group=AgentGroup.OPERATIONS,
                last_run=datetime.now() - timedelta(minutes=45),
                cooldown_minutes=30
            )
            orchestrator.register_agent(reg)

            # Should attempt to start (returns None because agent creation is mocked)
            result = await orchestrator.start_agent("cooldown_expired_test")
            # Returns None because _create_agent returns None

    @pytest.mark.asyncio
    async def test_start_agent_success(self, orchestrator):
        """Test successfully starting an agent."""
        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.start = AsyncMock(return_value=AgentResult(
            success=True,
            message="Agent completed",
            items_processed=5
        ))
        mock_agent.add_task = MagicMock()

        with patch.object(orchestrator, '_create_agent', return_value=mock_agent):
            reg = AgentRegistration(
                agent_id="success_test",
                agent_type="test",
                agent_class="TestAgent",
                group=AgentGroup.OPERATIONS
            )
            orchestrator.register_agent(reg)

            initial_completed = orchestrator.stats['tasks_completed']
            result = await orchestrator.start_agent("success_test")

            assert result is not None
            assert result.success is True
            assert orchestrator.stats['tasks_completed'] == initial_completed + 1
            assert orchestrator.agent_registry["success_test"].is_running is False
            assert orchestrator.agent_registry["success_test"].last_run is not None

    @pytest.mark.asyncio
    async def test_start_agent_failure(self, orchestrator):
        """Test starting an agent that fails."""
        mock_agent = MagicMock()
        mock_agent.start = AsyncMock(return_value=AgentResult(
            success=False,
            message="Agent failed",
            errors=["Error occurred"]
        ))
        mock_agent.add_task = MagicMock()

        with patch.object(orchestrator, '_create_agent', return_value=mock_agent):
            reg = AgentRegistration(
                agent_id="failure_test",
                agent_type="test",
                agent_class="TestAgent",
                group=AgentGroup.OPERATIONS
            )
            orchestrator.register_agent(reg)

            initial_failed = orchestrator.stats['tasks_failed']
            result = await orchestrator.start_agent("failure_test")

            assert result is not None
            assert result.success is False
            assert orchestrator.stats['tasks_failed'] == initial_failed + 1

    @pytest.mark.asyncio
    async def test_start_agent_with_task(self, orchestrator):
        """Test starting an agent with a task."""
        mock_agent = MagicMock()
        mock_agent.start = AsyncMock(return_value=AgentResult(success=True, message="OK"))
        mock_agent.add_task = MagicMock()

        with patch.object(orchestrator, '_create_agent', return_value=mock_agent):
            reg = AgentRegistration(
                agent_id="task_test",
                agent_type="test",
                agent_class="TestAgent",
                group=AgentGroup.OPERATIONS
            )
            orchestrator.register_agent(reg)

            task = AgentTask(
                task_id="test_task",
                task_type="test",
                payload={"data": "value"}
            )

            result = await orchestrator.start_agent("task_test", task)

            # Verify task was added to agent
            mock_agent.add_task.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_start_agent_exception(self, orchestrator):
        """Test starting an agent that raises an exception."""
        with patch.object(orchestrator, '_create_agent', side_effect=Exception("Test error")):
            reg = AgentRegistration(
                agent_id="exception_test",
                agent_type="test",
                agent_class="TestAgent",
                group=AgentGroup.OPERATIONS
            )
            orchestrator.register_agent(reg)

            result = await orchestrator.start_agent("exception_test")

            assert result is not None
            assert result.success is False
            assert "Test error" in result.message
            assert orchestrator.agent_registry["exception_test"].is_running is False

    @pytest.mark.asyncio
    async def test_stop_agent(self, orchestrator):
        """Test stopping a running agent."""
        mock_agent = MagicMock()
        mock_agent.stop = MagicMock()

        reg = AgentRegistration(
            agent_id="stop_test",
            agent_type="test",
            agent_class="TestAgent",
            group=AgentGroup.OPERATIONS,
            is_running=True
        )
        orchestrator.register_agent(reg)
        orchestrator.active_agents["stop_test"] = mock_agent

        await orchestrator.stop_agent("stop_test")

        mock_agent.stop.assert_called_once()
        assert "stop_test" not in orchestrator.active_agents
        assert orchestrator.agent_registry["stop_test"].is_running is False

    @pytest.mark.asyncio
    async def test_stop_agent_not_running(self, orchestrator):
        """Test stopping an agent that's not running."""
        # Should not raise error
        await orchestrator.stop_agent("not_running")

    def test_get_status_report(self, orchestrator):
        """Test getting status report."""
        report = orchestrator.get_status_report()

        assert 'orchestrator' in report
        assert 'agents' in report
        assert 'tasks' in report
        assert 'active_agents' in report

        assert report['orchestrator']['status'] == 'idle'
        assert report['orchestrator']['mode'] == 'idle'
        assert 'uptime' in report['orchestrator']

        assert 'registered' in report['agents']
        assert 'active' in report['agents']
        assert 'by_group' in report['agents']

        assert 'scheduled' in report['tasks']
        assert 'completed' in report['tasks']
        assert 'failed' in report['tasks']

    def test_get_status_report_with_scheduled_tasks(self, orchestrator):
        """Test status report shows next scheduled task."""
        task = ScheduledTask(
            task_id="next_task",
            agent_id="agent",
            task_type="test",
            schedule_time=datetime.now() + timedelta(hours=1)
        )
        orchestrator.schedule_task(task)

        report = orchestrator.get_status_report()
        assert report['next_scheduled'] is not None

    def test_get_agent_list(self, orchestrator):
        """Test getting list of all registered agents."""
        agent_list = orchestrator.get_agent_list()

        assert isinstance(agent_list, list)
        assert len(agent_list) > 0

        # Check first agent has required fields
        first_agent = agent_list[0]
        assert 'agent_id' in first_agent
        assert 'type' in first_agent
        assert 'class' in first_agent
        assert 'group' in first_agent
        assert 'enabled' in first_agent
        assert 'running' in first_agent
        assert 'priority' in first_agent

    def test_get_agent_list_filtered_by_group(self, orchestrator):
        """Test getting agents filtered by group."""
        state_agents = orchestrator.get_agent_list(group=AgentGroup.STATE)

        assert isinstance(state_agents, list)
        assert len(state_agents) > 0

        # All should be STATE group
        for agent in state_agents:
            assert agent['group'] == 'state'

    def test_get_agent_list_all_groups(self, orchestrator):
        """Test getting agents for each group."""
        for group in AgentGroup:
            agents = orchestrator.get_agent_list(group=group)
            assert isinstance(agents, list)

            # All returned agents should belong to requested group
            for agent in agents:
                assert agent['group'] == group.value

    @pytest.mark.asyncio
    async def test_execute_task_unknown_type(self, orchestrator):
        """Test executing task with unknown type."""
        task = AgentTask(
            task_id="unknown_task",
            task_type="unknown_type",
            payload={}
        )

        result = await orchestrator.execute_task(task)

        assert result.success is False
        assert "Unknown task type" in result.message

    @pytest.mark.asyncio
    async def test_execute_task_run_discovery(self, orchestrator):
        """Test executing run_discovery task."""
        with patch.object(orchestrator, 'run_state_discovery',
                         return_value={'states_processed': 5, 'successful': 5, 'failed': 0}):
            task = AgentTask(
                task_id="discovery_task",
                task_type="run_discovery",
                payload={'states': ['NY', 'CA']}
            )

            result = await orchestrator.execute_task(task)

            assert result.success is True
            assert "Discovery completed" in result.message

    @pytest.mark.asyncio
    async def test_execute_task_run_social(self, orchestrator):
        """Test executing run_social task."""
        with patch.object(orchestrator, 'run_social_media_campaign',
                         return_value=[]):
            task = AgentTask(
                task_id="social_task",
                task_type="run_social",
                payload={}
            )

            result = await orchestrator.execute_task(task)

            assert result.success is True
            assert "Social campaign completed" in result.message

    @pytest.mark.asyncio
    async def test_execute_task_run_maintenance(self, orchestrator):
        """Test executing run_maintenance task."""
        with patch.object(orchestrator, 'run_maintenance_cycle',
                         return_value=None):
            task = AgentTask(
                task_id="maintenance_task",
                task_type="run_maintenance",
                payload={}
            )

            result = await orchestrator.execute_task(task)

            assert result.success is True
            assert "Maintenance completed" in result.message

    @pytest.mark.asyncio
    async def test_process_scheduled_tasks_due(self, orchestrator):
        """Test processing scheduled tasks that are due."""
        # Schedule a task in the past (already due)
        past_time = datetime.now() - timedelta(minutes=5)
        task = ScheduledTask(
            task_id="due_task",
            agent_id="test_agent",
            task_type="test_task",
            schedule_time=past_time
        )
        orchestrator.schedule_task(task)

        with patch.object(orchestrator, 'start_agent', return_value=None):
            await orchestrator.process_scheduled_tasks()

            # Task should be removed from scheduled tasks
            assert task not in orchestrator.scheduled_tasks

    @pytest.mark.asyncio
    async def test_process_scheduled_tasks_not_due(self, orchestrator):
        """Test processing scheduled tasks that are not due."""
        # Schedule a task in the future
        future_time = datetime.now() + timedelta(hours=1)
        task = ScheduledTask(
            task_id="future_task",
            agent_id="test_agent",
            task_type="test_task",
            schedule_time=future_time
        )
        orchestrator.schedule_task(task)

        initial_count = len(orchestrator.scheduled_tasks)

        with patch.object(orchestrator, 'start_agent', return_value=None):
            await orchestrator.process_scheduled_tasks()

            # Task should still be in scheduled tasks
            assert len(orchestrator.scheduled_tasks) == initial_count
            assert task in orchestrator.scheduled_tasks

    @pytest.mark.asyncio
    async def test_process_scheduled_tasks_recurring(self, orchestrator):
        """Test processing recurring scheduled tasks."""
        past_time = datetime.now() - timedelta(minutes=5)
        task = ScheduledTask(
            task_id="recurring_task",
            agent_id="test_agent",
            task_type="test_task",
            schedule_time=past_time,
            recurrence="hourly"
        )
        orchestrator.schedule_task(task)

        with patch.object(orchestrator, 'start_agent', return_value=None):
            await orchestrator.process_scheduled_tasks()

            # Task should be rescheduled
            assert len(orchestrator.scheduled_tasks) > 0
            rescheduled = [t for t in orchestrator.scheduled_tasks if t.task_id == "recurring_task"]
            assert len(rescheduled) == 1
            assert rescheduled[0].schedule_time > datetime.now()

    def test_calculate_next_run_hourly(self, orchestrator):
        """Test calculating next run time for hourly recurrence."""
        last_run = datetime.now()
        next_run = orchestrator._calculate_next_run(last_run, "hourly")
        expected = last_run + timedelta(hours=1)

        # Allow small time difference
        assert abs((next_run - expected).total_seconds()) < 1

    def test_calculate_next_run_daily(self, orchestrator):
        """Test calculating next run time for daily recurrence."""
        last_run = datetime.now()
        next_run = orchestrator._calculate_next_run(last_run, "daily")
        expected = last_run + timedelta(days=1)

        assert abs((next_run - expected).total_seconds()) < 1

    def test_calculate_next_run_weekly(self, orchestrator):
        """Test calculating next run time for weekly recurrence."""
        last_run = datetime.now()
        next_run = orchestrator._calculate_next_run(last_run, "weekly")
        expected = last_run + timedelta(weeks=1)

        assert abs((next_run - expected).total_seconds()) < 1

    def test_calculate_next_run_unknown(self, orchestrator):
        """Test calculating next run time for unknown recurrence defaults to hourly."""
        last_run = datetime.now()
        next_run = orchestrator._calculate_next_run(last_run, "unknown")
        expected = last_run + timedelta(hours=1)

        assert abs((next_run - expected).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_create_agent_state_agent(self, orchestrator):
        """Test creating a state agent."""
        mock_state_agent = MagicMock()

        with patch('agents.orchestrator.get_state_agent', return_value=mock_state_agent):
            reg = AgentRegistration(
                agent_id="state_ny",
                agent_type="state_agent",
                agent_class="StateAgent",
                group=AgentGroup.STATE,
                config={'state_code': 'NY'}
            )

            agent = await orchestrator._create_agent(reg)

            assert agent == mock_state_agent

    @pytest.mark.asyncio
    async def test_create_agent_specialized_not_implemented(self, orchestrator):
        """Test creating a specialized agent that's not implemented returns None."""
        reg = AgentRegistration(
            agent_id="unimplemented",
            agent_type="specialized_agent",
            agent_class="UnimplementedAgent",
            group=AgentGroup.OPERATIONS
        )

        agent = await orchestrator._create_agent(reg)

        assert agent is None

    @pytest.mark.asyncio
    async def test_create_agent_exception(self, orchestrator):
        """Test creating an agent that raises exception returns None."""
        with patch('agents.orchestrator.get_state_agent', side_effect=Exception("Creation failed")):
            reg = AgentRegistration(
                agent_id="state_error",
                agent_type="state_agent",
                agent_class="StateAgent",
                group=AgentGroup.STATE,
                config={'state_code': 'XX'}
            )

            agent = await orchestrator._create_agent(reg)

            assert agent is None

    def test_orchestrator_has_semaphores(self, orchestrator):
        """Test orchestrator has semaphores for all groups."""
        assert len(orchestrator.semaphores) == len(AgentGroup)

        for group in AgentGroup:
            assert group in orchestrator.semaphores
            assert isinstance(orchestrator.semaphores[group], asyncio.Semaphore)

    def test_orchestrator_mode_transitions(self, orchestrator):
        """Test orchestrator mode can be changed."""
        assert orchestrator.mode == OrchestratorMode.IDLE

        orchestrator.mode = OrchestratorMode.DISCOVERY
        assert orchestrator.mode == OrchestratorMode.DISCOVERY

        orchestrator.mode = OrchestratorMode.MAINTENANCE
        assert orchestrator.mode == OrchestratorMode.MAINTENANCE

        orchestrator.mode = OrchestratorMode.IDLE
        assert orchestrator.mode == OrchestratorMode.IDLE

    @pytest.mark.asyncio
    async def test_run_state_discovery_all_states(self, orchestrator):
        """Test running state discovery for all states."""
        with patch.object(orchestrator, 'start_agent', return_value=AgentResult(success=True, message="OK")):
            # Call with no parameters (all states)
            result = await orchestrator.run_state_discovery()

            assert 'states_processed' in result
            assert 'successful' in result
            assert 'failed' in result
            assert result['states_processed'] > 0

    @pytest.mark.asyncio
    async def test_run_state_discovery_specific_states(self, orchestrator):
        """Test running state discovery for specific states."""
        with patch.object(orchestrator, 'start_agent', return_value=AgentResult(success=True, message="OK")):
            result = await orchestrator.run_state_discovery(states=['NY', 'CA', 'TX'])

            assert result['states_processed'] == 3

    @pytest.mark.asyncio
    async def test_run_social_media_campaign(self, orchestrator):
        """Test running social media campaign."""
        with patch.object(orchestrator, 'start_agent', return_value=AgentResult(success=True, message="OK")):
            result = await orchestrator.run_social_media_campaign()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_run_maintenance_cycle(self, orchestrator):
        """Test running maintenance cycle."""
        with patch.object(orchestrator, 'start_agent', return_value=None):
            await orchestrator.run_maintenance_cycle()

            # Should complete without error
            assert orchestrator.mode == OrchestratorMode.IDLE


class TestGetOrchestrator:
    """Tests for get_orchestrator function."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Reset singleton before and after each test."""
        AgentOrchestrator._instance = None
        BaseAgent._registry.clear()
        yield
        AgentOrchestrator._instance = None
        BaseAgent._registry.clear()

    def test_get_orchestrator_returns_instance(self):
        """Test get_orchestrator returns an orchestrator instance."""
        with patch('agents.orchestrator.get_all_state_agents'):
            with patch('agents.orchestrator.get_state_agent'):
                with patch('agents.base_agent.init_db'):
                    with patch('agents.base_agent.SessionLocal'):
                        orch = get_orchestrator()

                        assert isinstance(orch, AgentOrchestrator)
                        assert orch.agent_id == "orchestrator"

    def test_get_orchestrator_returns_same_instance(self):
        """Test get_orchestrator always returns the same instance."""
        with patch('agents.orchestrator.get_all_state_agents'):
            with patch('agents.orchestrator.get_state_agent'):
                with patch('agents.base_agent.init_db'):
                    with patch('agents.base_agent.SessionLocal'):
                        orch1 = get_orchestrator()
                        orch2 = get_orchestrator()

                        assert orch1 is orch2
