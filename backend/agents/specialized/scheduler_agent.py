#!/usr/bin/env python3
"""
===============================================================================
Scheduler Agent - Task Scheduling & Automation
===============================================================================
Manages scheduled tasks, cron jobs, and automated workflows.

Features:
- Task scheduling
- Recurring job management
- Workflow automation
- Time-based triggers
- Dependency management
- Schedule optimization
- Job queue management

Cooperates with: Orchestrator, ALL agents
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


@dataclass
class ScheduledJob:
    job_id: str
    name: str
    agent_id: str
    task_type: str
    schedule: str  # cron expression or interval
    next_run: datetime
    enabled: bool = True
    last_run: datetime = None
    payload: Dict = field(default_factory=dict)


class SchedulerAgent(CooperativeMixin, BaseAgent):
    """Task scheduling agent."""

    def __init__(self):
        BaseAgent.__init__(self, agent_id="scheduler", agent_name="Scheduler Agent",
                          agent_type="specialized_agent", description="Task scheduling and automation")
        CooperativeMixin.__init__(self)
        self.jobs: Dict[str, ScheduledJob] = {}
        self.register_handler('schedule_job', self._handle_schedule)
        self.register_handler('get_schedule', self._handle_get_schedule)
        self.register_handler('cancel_job', self._handle_cancel)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        task.started_at = datetime.now()
        if task.task_type == "schedule_job":
            result = await self.schedule_job(task.payload)
        elif task.task_type == "run_scheduled":
            result = await self.run_scheduled_jobs()
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        task.completed_at = datetime.now()
        return AgentResult(success=True, message="Scheduler task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Scheduler Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            await self.check_scheduled_jobs()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Scheduler Agent completed")

    async def schedule_job(self, params: Dict) -> Dict:
        job = ScheduledJob(
            job_id=f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=params.get('name', 'Unnamed'),
            agent_id=params.get('agent_id', ''),
            task_type=params.get('task_type', ''),
            schedule=params.get('schedule', 'daily'),
            next_run=self._calculate_next_run(params.get('schedule', 'daily')),
            payload=params.get('payload', {})
        )
        self.jobs[job.job_id] = job
        return {'job_id': job.job_id, 'next_run': job.next_run.isoformat()}

    async def check_scheduled_jobs(self):
        now = datetime.now()
        for job in self.jobs.values():
            if job.enabled and job.next_run <= now:
                await self._execute_job(job)
                job.last_run = now
                job.next_run = self._calculate_next_run(job.schedule)

    async def _execute_job(self, job: ScheduledJob):
        self.handoff_to_agent(job.agent_id, job.task_type, job.name, job.payload)

    def _calculate_next_run(self, schedule: str) -> datetime:
        now = datetime.now()
        if schedule == 'hourly': return now + timedelta(hours=1)
        if schedule == 'daily': return now + timedelta(days=1)
        if schedule == 'weekly': return now + timedelta(weeks=1)
        return now + timedelta(hours=1)

    async def run_scheduled_jobs(self) -> Dict:
        await self.check_scheduled_jobs()
        return {'checked': len(self.jobs)}

    async def _handle_schedule(self, payload: Dict) -> Dict:
        return await self.schedule_job(payload)

    async def _handle_get_schedule(self, payload: Dict) -> Dict:
        return {'jobs': [{k: str(v) for k, v in j.__dict__.items()} for j in self.jobs.values()]}

    async def _handle_cancel(self, payload: Dict) -> Dict:
        job_id = payload.get('job_id')
        if job_id in self.jobs:
            del self.jobs[job_id]
            return {'cancelled': True}
        return {'cancelled': False}
