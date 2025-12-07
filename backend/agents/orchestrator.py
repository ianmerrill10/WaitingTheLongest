#!/usr/bin/env python3
"""
===============================================================================
Agent Orchestrator - Central Command for All AI Agents
===============================================================================
The brain that coordinates and manages all agents in the Waiting The Longest
system. Handles scheduling, load balancing, inter-agent communication, and
overall system health monitoring.

Features:
- Manages 50 state agents for nationwide shelter discovery
- Coordinates 32+ specialized agents for various tasks
- Priority-based task scheduling
- Real-time monitoring dashboard
- Automatic failover and recovery
- Resource allocation and load balancing
- Centralized logging and reporting

Author: Waiting The Longest Development Team
===============================================================================
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

# Add parent directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.base_agent import (
    BaseAgent, AgentStatus, AgentTask, AgentResult,
    TaskPriority, generate_task_id
)
from agents.state_agents import get_all_state_agents, get_state_agent, STATE_DATA


class OrchestratorMode(Enum):
    """Operating modes for the orchestrator"""
    IDLE = "idle"
    DISCOVERY = "discovery"      # Running state agents for shelter discovery
    MAINTENANCE = "maintenance"  # Running maintenance/cleanup tasks
    MARKETING = "marketing"      # Running social media/marketing agents
    FULL = "full"               # All agents active
    EMERGENCY = "emergency"     # Critical operations only


class AgentGroup(Enum):
    """Agent groupings for coordinated operations"""
    STATE = "state"
    SOCIAL_MEDIA = "social_media"
    DATA_PROCESSING = "data_processing"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    MONITORING = "monitoring"


@dataclass
class AgentRegistration:
    """Registration info for a managed agent"""
    agent_id: str
    agent_type: str
    agent_class: str
    group: AgentGroup
    priority: int = 5
    max_concurrent: int = 1
    cooldown_minutes: int = 30
    last_run: Optional[datetime] = None
    is_running: bool = False
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledTask:
    """A scheduled task for an agent"""
    task_id: str
    agent_id: str
    task_type: str
    schedule_time: datetime
    recurrence: Optional[str] = None  # "hourly", "daily", "weekly"
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)


class AgentOrchestrator(BaseAgent):
    """
    Central orchestrator that manages all agents in the system.

    Responsibilities:
    - Agent lifecycle management (start, stop, restart)
    - Task scheduling and distribution
    - Load balancing across agents
    - Health monitoring and recovery
    - Resource management
    - Centralized reporting
    """

    # Singleton instance
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Skip re-initialization if already done
        if hasattr(self, '_initialized') and self._initialized:
            return

        super().__init__(
            agent_id="orchestrator",
            agent_name="Agent Orchestrator",
            agent_type="orchestrator",
            description="Central command for all AI agents"
        )

        self.mode = OrchestratorMode.IDLE

        # Agent registry
        self.agent_registry: Dict[str, AgentRegistration] = {}
        self.active_agents: Dict[str, BaseAgent] = {}

        # Scheduling
        self.scheduled_tasks: List[ScheduledTask] = []
        self.task_history: List[Dict] = []

        # Concurrency control
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.semaphores: Dict[AgentGroup, asyncio.Semaphore] = {
            AgentGroup.STATE: asyncio.Semaphore(5),  # 5 states at a time
            AgentGroup.SOCIAL_MEDIA: asyncio.Semaphore(3),
            AgentGroup.DATA_PROCESSING: asyncio.Semaphore(2),
            AgentGroup.MARKETING: asyncio.Semaphore(2),
            AgentGroup.OPERATIONS: asyncio.Semaphore(3),
            AgentGroup.MONITORING: asyncio.Semaphore(2),
        }

        # Statistics
        self.stats = {
            'agents_registered': 0,
            'tasks_scheduled': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'uptime_start': datetime.now(),
        }

        # Initialize agent registrations
        self._register_all_agents()

        self._initialized = True
        self.logger.info("Agent Orchestrator initialized")

    def _register_all_agents(self):
        """Register all known agents with the orchestrator"""

        # Register all 50 state agents
        for state_code in STATE_DATA.keys():
            self.register_agent(AgentRegistration(
                agent_id=f"state_{state_code.lower()}",
                agent_type="state_agent",
                agent_class="StateAgent",
                group=AgentGroup.STATE,
                priority=5,
                max_concurrent=1,
                cooldown_minutes=360,  # 6 hours between runs
                config={'state_code': state_code}
            ))

        # Register specialized agents
        specialized_agents = [
            # Social Media Group
            ("marketing", "MarketingAgent", AgentGroup.MARKETING, 8),
            ("tiktok", "TikTokAgent", AgentGroup.SOCIAL_MEDIA, 7),
            ("instagram", "InstagramAgent", AgentGroup.SOCIAL_MEDIA, 7),
            ("facebook", "FacebookAgent", AgentGroup.SOCIAL_MEDIA, 7),

            # Data Processing Group
            ("librarian", "LibrarianAgent", AgentGroup.DATA_PROCESSING, 6),
            ("data_quality", "DataQualityAgent", AgentGroup.DATA_PROCESSING, 9),
            ("intake_specialist", "IntakeSpecialistAgent", AgentGroup.DATA_PROCESSING, 8),
            ("image_processing", "ImageProcessingAgent", AgentGroup.DATA_PROCESSING, 5),
            ("translation", "TranslationAgent", AgentGroup.DATA_PROCESSING, 4),

            # Operations Group
            ("debugging", "DebuggingAgent", AgentGroup.OPERATIONS, 10),
            ("accounting", "AccountingAgent", AgentGroup.OPERATIONS, 6),
            ("scheduler", "SchedulerAgent", AgentGroup.OPERATIONS, 7),
            ("backup", "BackupAgent", AgentGroup.OPERATIONS, 8),
            ("compliance", "ComplianceAgent", AgentGroup.OPERATIONS, 7),

            # Marketing Group
            ("seo", "SEOAgent", AgentGroup.MARKETING, 6),
            ("email_campaign", "EmailCampaignAgent", AgentGroup.MARKETING, 5),
            ("content_writer", "ContentWriterAgent", AgentGroup.MARKETING, 6),
            ("video_generator", "VideoGeneratorAgent", AgentGroup.MARKETING, 4),

            # Monitoring Group
            ("alert_monitor", "AlertMonitorAgent", AgentGroup.MONITORING, 10),
            ("api_monitor", "APIMonitorAgent", AgentGroup.MONITORING, 9),
            ("analytics", "AnalyticsAgent", AgentGroup.MONITORING, 5),
            ("sentiment_analysis", "SentimentAnalysisAgent", AgentGroup.MONITORING, 4),
            ("competitor_watch", "CompetitorWatchAgent", AgentGroup.MONITORING, 3),

            # Operations Extended
            ("donation_tracker", "DonationTrackerAgent", AgentGroup.OPERATIONS, 6),
            ("volunteer_coordinator", "VolunteerCoordinatorAgent", AgentGroup.OPERATIONS, 5),
            ("adoption_matcher", "AdoptionMatcherAgent", AgentGroup.OPERATIONS, 8),
            ("notification", "NotificationAgent", AgentGroup.OPERATIONS, 7),
            ("report_generator", "ReportGeneratorAgent", AgentGroup.OPERATIONS, 4),
            ("chat_support", "ChatSupportAgent", AgentGroup.OPERATIONS, 8),
        ]

        for agent_id, agent_class, group, priority in specialized_agents:
            self.register_agent(AgentRegistration(
                agent_id=agent_id,
                agent_type="specialized_agent",
                agent_class=agent_class,
                group=group,
                priority=priority,
                max_concurrent=1,
                cooldown_minutes=60,
            ))

        self.stats['agents_registered'] = len(self.agent_registry)
        self.logger.info(f"Registered {len(self.agent_registry)} agents")

    def register_agent(self, registration: AgentRegistration):
        """Register an agent with the orchestrator"""
        self.agent_registry[registration.agent_id] = registration
        self.logger.debug(f"Registered agent: {registration.agent_id}")

    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")

    def enable_agent(self, agent_id: str):
        """Enable an agent"""
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id].enabled = True
            self.logger.info(f"Enabled agent: {agent_id}")

    def disable_agent(self, agent_id: str):
        """Disable an agent"""
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id].enabled = False
            self.logger.info(f"Disabled agent: {agent_id}")

    async def start_agent(self, agent_id: str, task: Optional[AgentTask] = None) -> Optional[AgentResult]:
        """Start a specific agent"""
        if agent_id not in self.agent_registry:
            self.logger.error(f"Unknown agent: {agent_id}")
            return None

        registration = self.agent_registry[agent_id]

        if not registration.enabled:
            self.logger.warning(f"Agent {agent_id} is disabled")
            return None

        if registration.is_running:
            self.logger.warning(f"Agent {agent_id} is already running")
            return None

        # Check cooldown
        if registration.last_run:
            cooldown_end = registration.last_run + timedelta(minutes=registration.cooldown_minutes)
            if datetime.now() < cooldown_end:
                remaining = (cooldown_end - datetime.now()).seconds // 60
                self.logger.info(f"Agent {agent_id} in cooldown ({remaining} min remaining)")
                return None

        # Get semaphore for this agent's group
        semaphore = self.semaphores[registration.group]

        async with semaphore:
            try:
                registration.is_running = True

                # Instantiate the agent
                agent = await self._create_agent(registration)
                if not agent:
                    return None

                self.active_agents[agent_id] = agent

                # Add task if provided
                if task:
                    agent.add_task(task)

                # Run the agent
                self.logger.info(f"Starting agent: {agent_id}")
                result = await agent.start()

                registration.last_run = datetime.now()
                registration.is_running = False

                # Update stats
                if result.success:
                    self.stats['tasks_completed'] += 1
                else:
                    self.stats['tasks_failed'] += 1

                # Clean up
                if agent_id in self.active_agents:
                    del self.active_agents[agent_id]

                return result

            except Exception as e:
                self.logger.error(f"Error running agent {agent_id}: {e}", exc_info=True)
                registration.is_running = False
                return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def _create_agent(self, registration: AgentRegistration) -> Optional[BaseAgent]:
        """Create an agent instance from registration"""
        try:
            if registration.agent_type == "state_agent":
                state_code = registration.config.get('state_code')
                return get_state_agent(state_code)
            else:
                # For specialized agents, we'll import and create them dynamically
                # This will be implemented as we create each agent
                self.logger.warning(f"Agent class {registration.agent_class} not yet implemented")
                return None
        except Exception as e:
            self.logger.error(f"Failed to create agent: {e}")
            return None

    async def stop_agent(self, agent_id: str):
        """Stop a running agent"""
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            agent.stop()
            del self.active_agents[agent_id]

            if agent_id in self.agent_registry:
                self.agent_registry[agent_id].is_running = False

            self.logger.info(f"Stopped agent: {agent_id}")

    def schedule_task(self, task: ScheduledTask):
        """Schedule a task for future execution"""
        self.scheduled_tasks.append(task)
        self.scheduled_tasks.sort(key=lambda t: t.schedule_time)
        self.stats['tasks_scheduled'] += 1
        self.logger.info(f"Scheduled task {task.task_id} for {task.schedule_time}")

    def cancel_scheduled_task(self, task_id: str):
        """Cancel a scheduled task"""
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t.task_id != task_id]
        self.logger.info(f"Cancelled scheduled task: {task_id}")

    async def run_state_discovery(self, states: Optional[List[str]] = None, region: Optional[str] = None):
        """
        Run shelter discovery for specified states or regions.

        Args:
            states: List of state codes (e.g., ['NY', 'CA']) or None for all
            region: Region name (e.g., 'Northeast') or None
        """
        self.mode = OrchestratorMode.DISCOVERY

        # Determine which states to process
        if states:
            target_states = states
        elif region:
            target_states = [
                code for code, data in STATE_DATA.items()
                if data['region'] == region
            ]
        else:
            target_states = list(STATE_DATA.keys())

        self.logger.info(f"Starting discovery for {len(target_states)} states")

        # Create tasks for all states
        tasks = []
        for state_code in target_states:
            agent_id = f"state_{state_code.lower()}"
            task = AgentTask(
                task_id=generate_task_id("discovery"),
                task_type="shelter_discovery",
                payload={'state_code': state_code},
                priority=TaskPriority.HIGH
            )
            tasks.append((agent_id, task))

        # Run agents in batches (controlled by semaphore)
        results = await asyncio.gather(*[
            self.start_agent(agent_id, task)
            for agent_id, task in tasks
        ], return_exceptions=True)

        # Summarize results
        successful = sum(1 for r in results if isinstance(r, AgentResult) and r.success)
        failed = len(results) - successful

        self.mode = OrchestratorMode.IDLE

        return {
            'states_processed': len(target_states),
            'successful': successful,
            'failed': failed,
            'results': [r.to_dict() if isinstance(r, AgentResult) else str(r) for r in results]
        }

    async def run_social_media_campaign(self):
        """Run all social media agents for a coordinated campaign"""
        self.mode = OrchestratorMode.MARKETING

        social_agents = ['tiktok', 'instagram', 'facebook', 'marketing']

        results = await asyncio.gather(*[
            self.start_agent(agent_id) for agent_id in social_agents
        ], return_exceptions=True)

        self.mode = OrchestratorMode.IDLE
        return results

    async def run_maintenance_cycle(self):
        """Run maintenance and data quality agents"""
        self.mode = OrchestratorMode.MAINTENANCE

        maintenance_agents = [
            'data_quality',
            'backup',
            'compliance',
            'debugging'
        ]

        for agent_id in maintenance_agents:
            await self.start_agent(agent_id)

        self.mode = OrchestratorMode.IDLE

    async def process_scheduled_tasks(self):
        """Process any scheduled tasks that are due"""
        now = datetime.now()

        due_tasks = [t for t in self.scheduled_tasks if t.schedule_time <= now]

        for task in due_tasks:
            self.scheduled_tasks.remove(task)

            agent_task = AgentTask(
                task_id=task.task_id,
                task_type=task.task_type,
                payload=task.payload,
                priority=task.priority
            )

            await self.start_agent(task.agent_id, agent_task)

            # Re-schedule if recurring
            if task.recurrence:
                new_time = self._calculate_next_run(task.schedule_time, task.recurrence)
                task.schedule_time = new_time
                self.schedule_task(task)

    def _calculate_next_run(self, last_run: datetime, recurrence: str) -> datetime:
        """Calculate next run time based on recurrence"""
        if recurrence == "hourly":
            return last_run + timedelta(hours=1)
        elif recurrence == "daily":
            return last_run + timedelta(days=1)
        elif recurrence == "weekly":
            return last_run + timedelta(weeks=1)
        else:
            return last_run + timedelta(hours=1)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute an orchestrator task"""
        if task.task_type == "run_discovery":
            states = task.payload.get('states')
            region = task.payload.get('region')
            result = await self.run_state_discovery(states, region)
            return AgentResult(
                success=True,
                message="Discovery completed",
                data=result,
                items_processed=result['states_processed']
            )
        elif task.task_type == "run_social":
            await self.run_social_media_campaign()
            return AgentResult(success=True, message="Social campaign completed")
        elif task.task_type == "run_maintenance":
            await self.run_maintenance_cycle()
            return AgentResult(success=True, message="Maintenance completed")
        else:
            return AgentResult(success=False, message=f"Unknown task type: {task.task_type}")

    async def run(self) -> AgentResult:
        """Main orchestrator loop"""
        self.logger.info("Orchestrator main loop starting")

        while self.status == AgentStatus.RUNNING:
            try:
                # Process scheduled tasks
                await self.process_scheduled_tasks()

                # Process any queued tasks
                task = self.get_next_task()
                if task:
                    result = await self.execute_task(task)
                    self.task_history.append({
                        'task_id': task.task_id,
                        'result': result.to_dict(),
                        'completed_at': datetime.now().isoformat()
                    })

                # Small delay to prevent busy loop
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Orchestrator error: {e}", exc_info=True)
                await asyncio.sleep(5)

        return AgentResult(
            success=True,
            message="Orchestrator stopped",
            data={'tasks_processed': len(self.task_history)}
        )

    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        uptime = datetime.now() - self.stats['uptime_start']

        return {
            'orchestrator': {
                'status': self.status.value,
                'mode': self.mode.value,
                'uptime': str(uptime),
            },
            'agents': {
                'registered': self.stats['agents_registered'],
                'active': len(self.active_agents),
                'by_group': {
                    group.value: len([
                        r for r in self.agent_registry.values()
                        if r.group == group
                    ])
                    for group in AgentGroup
                }
            },
            'tasks': {
                'scheduled': len(self.scheduled_tasks),
                'completed': self.stats['tasks_completed'],
                'failed': self.stats['tasks_failed'],
            },
            'active_agents': list(self.active_agents.keys()),
            'next_scheduled': (
                self.scheduled_tasks[0].schedule_time.isoformat()
                if self.scheduled_tasks else None
            )
        }

    def get_agent_list(self, group: Optional[AgentGroup] = None) -> List[Dict]:
        """Get list of registered agents"""
        agents = self.agent_registry.values()

        if group:
            agents = [a for a in agents if a.group == group]

        return [
            {
                'agent_id': a.agent_id,
                'type': a.agent_type,
                'class': a.agent_class,
                'group': a.group.value,
                'enabled': a.enabled,
                'running': a.is_running,
                'last_run': a.last_run.isoformat() if a.last_run else None,
                'priority': a.priority
            }
            for a in agents
        ]


# Singleton accessor
def get_orchestrator() -> AgentOrchestrator:
    """Get the singleton orchestrator instance"""
    return AgentOrchestrator()


# CLI interface
async def main():
    """Main entry point for CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Orchestrator CLI")
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--list-agents', action='store_true', help='List all agents')
    parser.add_argument('--discovery', nargs='*', help='Run discovery (optional: state codes)')
    parser.add_argument('--region', type=str, help='Run discovery for region')
    parser.add_argument('--social', action='store_true', help='Run social media campaign')
    parser.add_argument('--maintenance', action='store_true', help='Run maintenance cycle')
    parser.add_argument('--start', type=str, help='Start specific agent')
    parser.add_argument('--stop', type=str, help='Stop specific agent')

    args = parser.parse_args()

    orchestrator = get_orchestrator()

    if args.status:
        status = orchestrator.get_status_report()
        print(json.dumps(status, indent=2))

    elif args.list_agents:
        agents = orchestrator.get_agent_list()
        print(f"\n{'='*70}")
        print(f"Registered Agents: {len(agents)}")
        print(f"{'='*70}\n")

        for group in AgentGroup:
            group_agents = [a for a in agents if a['group'] == group.value]
            if group_agents:
                print(f"\n{group.value.upper()} ({len(group_agents)} agents):")
                print("-" * 40)
                for a in group_agents:
                    status = "🟢" if a['enabled'] else "🔴"
                    running = "▶️" if a['running'] else ""
                    print(f"  {status} {a['agent_id']:30} {running}")

    elif args.discovery is not None:
        states = args.discovery if args.discovery else None
        result = await orchestrator.run_state_discovery(states=states, region=args.region)
        print(json.dumps(result, indent=2))

    elif args.social:
        await orchestrator.run_social_media_campaign()
        print("Social media campaign completed")

    elif args.maintenance:
        await orchestrator.run_maintenance_cycle()
        print("Maintenance cycle completed")

    elif args.start:
        result = await orchestrator.start_agent(args.start)
        if result:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Failed to start agent: {args.start}")

    elif args.stop:
        await orchestrator.stop_agent(args.stop)
        print(f"Stopped agent: {args.stop}")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
