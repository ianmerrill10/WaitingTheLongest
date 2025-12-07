#!/usr/bin/env python3
"""
===============================================================================
Email Campaign Agent - Email Marketing Management
===============================================================================
Manages email campaigns, newsletters, and automated email sequences.

Features:
- Newsletter creation and sending
- Adoption follow-up sequences
- Shelter update notifications
- Donation thank-you emails
- Campaign analytics
- List segmentation
- A/B testing

Cooperates with: Marketing, Analytics, ContentWriter, Notification
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class EmailCampaignAgent(CooperativeMixin, BaseAgent):
    """Email marketing campaign agent."""

    def __init__(self):
        BaseAgent.__init__(self, agent_id="email_campaign", agent_name="Email Campaign Agent",
                          agent_type="specialized_agent", description="Email marketing management")
        CooperativeMixin.__init__(self)
        self.campaigns: List[Dict] = []
        self.templates: Dict[str, str] = {}
        self.register_handler('create_campaign', self._handle_campaign)
        self.register_handler('send_newsletter', self._handle_newsletter)
        self.register_handler('get_stats', self._handle_stats)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        task.started_at = datetime.now()
        if task.task_type == "create_campaign":
            result = await self.create_campaign(task.payload)
        elif task.task_type == "send_newsletter":
            result = await self.send_newsletter(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        task.completed_at = datetime.now()
        return AgentResult(success=True, message="Email task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Email Campaign Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Email Agent completed")

    async def create_campaign(self, params: Dict) -> Dict:
        campaign = {
            'id': f"campaign_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'name': params.get('name', 'Untitled'),
            'subject': params.get('subject', ''),
            'template': params.get('template', 'default'),
            'recipients': params.get('recipients', []),
            'status': 'draft',
            'stats': {'sent': 0, 'opened': 0, 'clicked': 0}
        }
        self.campaigns.append(campaign)
        return campaign

    async def send_newsletter(self, params: Dict) -> Dict:
        subject = params.get('subject', 'Weekly Update')
        content = await self.request_from_agent('content_writer', 'write_newsletter', params)
        return {'subject': subject, 'content': content, 'status': 'queued'}

    async def _handle_campaign(self, payload: Dict) -> Dict:
        return await self.create_campaign(payload)

    async def _handle_newsletter(self, payload: Dict) -> Dict:
        return await self.send_newsletter(payload)

    async def _handle_stats(self, payload: Dict) -> Dict:
        return {'total_campaigns': len(self.campaigns), 'campaigns': self.campaigns[-5:]}
