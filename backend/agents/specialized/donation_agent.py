#!/usr/bin/env python3
"""
===============================================================================
Donation Tracker Agent - Donation Management
===============================================================================
Tracks donations, fundraisers, and donor management.

Cooperates with: Accounting, Facebook, Notification, ReportGenerator
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
from decimal import Decimal
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class DonationTrackerAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="donation_tracker", agent_name="Donation Tracker Agent",
                          agent_type="specialized_agent", description="Donation tracking and management")
        CooperativeMixin.__init__(self)
        self.donations: List[Dict] = []
        self.fundraisers: List[Dict] = []
        self.register_handler('record_donation', self._handle_donation)
        self.register_handler('track_fundraiser', self._handle_fundraiser)
        self.register_handler('get_total', self._handle_total)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "record_donation":
            result = await self.record_donation(task.payload)
        elif task.task_type == "create_fundraiser":
            result = await self.create_fundraiser(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Donation task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Donation Tracker Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Donation Agent completed")

    async def record_donation(self, params: Dict) -> Dict:
        donation = {
            'id': f"don_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'amount': float(params.get('amount', 0)),
            'donor': params.get('donor', 'Anonymous'),
            'purpose': params.get('purpose', 'general'),
            'date': datetime.now().isoformat()
        }
        self.donations.append(donation)
        await self.request_from_agent('accounting', 'record_donation', donation)
        self.share_discovery(DataCategory.ANALYTICS, 'New donation received', donation, tags=['donation'])
        return donation

    async def create_fundraiser(self, params: Dict) -> Dict:
        fundraiser = {
            'id': f"fund_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'title': params.get('title', ''),
            'goal': float(params.get('goal', 0)),
            'raised': 0,
            'status': 'active'
        }
        self.fundraisers.append(fundraiser)
        return fundraiser

    async def _handle_donation(self, payload: Dict) -> Dict:
        return await self.record_donation(payload)
    async def _handle_fundraiser(self, payload: Dict) -> Dict:
        return await self.create_fundraiser(payload)
    async def _handle_total(self, payload: Dict) -> Dict:
        return {'total': sum(d['amount'] for d in self.donations), 'count': len(self.donations)}
