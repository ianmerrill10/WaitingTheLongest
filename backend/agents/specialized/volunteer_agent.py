#!/usr/bin/env python3
"""
===============================================================================
Volunteer Coordinator Agent - Volunteer Management
===============================================================================
Manages volunteer scheduling, tasks, and coordination.

Cooperates with: Scheduler, Notification, Librarian
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class VolunteerCoordinatorAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="volunteer_coordinator", agent_name="Volunteer Coordinator Agent",
                          agent_type="specialized_agent", description="Volunteer management and scheduling")
        CooperativeMixin.__init__(self)
        self.volunteers: List[Dict] = []
        self.shifts: List[Dict] = []
        self.register_handler('register_volunteer', self._handle_register)
        self.register_handler('schedule_shift', self._handle_shift)
        self.register_handler('get_schedule', self._handle_schedule)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "register_volunteer":
            result = await self.register_volunteer(task.payload)
        elif task.task_type == "schedule_shift":
            result = await self.schedule_shift(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Volunteer task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Volunteer Coordinator Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Volunteer Agent completed")

    async def register_volunteer(self, params: Dict) -> Dict:
        volunteer = {
            'id': f"vol_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'name': params.get('name', ''),
            'email': params.get('email', ''),
            'skills': params.get('skills', []),
            'availability': params.get('availability', []),
            'registered_at': datetime.now().isoformat()
        }
        self.volunteers.append(volunteer)
        return volunteer

    async def schedule_shift(self, params: Dict) -> Dict:
        shift = {
            'id': f"shift_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'volunteer_id': params.get('volunteer_id'),
            'date': params.get('date'),
            'time': params.get('time'),
            'task': params.get('task', 'general')
        }
        self.shifts.append(shift)
        return shift

    async def _handle_register(self, payload: Dict) -> Dict:
        return await self.register_volunteer(payload)
    async def _handle_shift(self, payload: Dict) -> Dict:
        return await self.schedule_shift(payload)
    async def _handle_schedule(self, payload: Dict) -> Dict:
        return {'volunteers': len(self.volunteers), 'shifts': self.shifts[-10:]}
