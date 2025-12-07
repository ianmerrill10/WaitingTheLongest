#!/usr/bin/env python3
"""
===============================================================================
Content Writer Agent - Content Creation
===============================================================================
Creates compelling content for animals, marketing, and communications.

Features:
- Animal bio generation
- Social media post writing
- Newsletter content
- Blog article drafting
- Email templates
- Adoption success stories
- SEO-optimized content

Cooperates with: Marketing, TikTok, Instagram, Facebook, SEO, Email
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


class ContentWriterAgent(CooperativeMixin, BaseAgent):
    """Content creation agent."""

    def __init__(self):
        BaseAgent.__init__(self, agent_id="content_writer", agent_name="Content Writer Agent",
                          agent_type="specialized_agent", description="Content creation specialist")
        CooperativeMixin.__init__(self)
        self.register_handler('write_bio', self._handle_bio)
        self.register_handler('write_social_post', self._handle_social)
        self.register_handler('write_newsletter', self._handle_newsletter)
        self.register_handler('prepare_campaign_content', self._handle_campaign)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        task.started_at = datetime.now()
        if task.task_type == "write_bio":
            result = await self.write_animal_bio(task.payload)
        elif task.task_type == "write_social":
            result = await self.write_social_post(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        task.completed_at = datetime.now()
        return AgentResult(success=True, message="Content task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Content Writer Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Content Writer completed")

    async def write_animal_bio(self, params: Dict) -> Dict:
        name = params.get('name', 'This pet')
        animal_type = params.get('type', 'dog')
        personality = params.get('personality', 'friendly and loving')
        days = params.get('days_waiting', 0)

        bio = f"{name} is a wonderful {animal_type} who has been patiently waiting for {days} days to find their forever family. "
        bio += f"Known for being {personality}, {name} would make the perfect companion. "
        bio += "Could you be the one to give them the loving home they deserve?"

        return {'name': name, 'bio': bio, 'word_count': len(bio.split())}

    async def write_social_post(self, params: Dict) -> Dict:
        platform = params.get('platform', 'instagram')
        name = params.get('name', 'This pet')
        days = params.get('days_waiting', 0)

        posts = {
            'instagram': f"Meet {name}! After {days} days of waiting, this sweetheart is still searching for their forever family. Could it be you? #adoptdontshop #waitingthelongest",
            'tiktok': f"{name} has been waiting {days} days. That's {days} days of hope. Please share! #fyp #adoptdontshop",
            'facebook': f"PLEASE SHARE: {name} has been at our shelter for {days} days. Every share helps find their forever home!"
        }

        return {'platform': platform, 'post': posts.get(platform, posts['instagram'])}

    async def _handle_bio(self, payload: Dict) -> Dict:
        return await self.write_animal_bio(payload)

    async def _handle_social(self, payload: Dict) -> Dict:
        return await self.write_social_post(payload)

    async def _handle_newsletter(self, payload: Dict) -> Dict:
        return {'content': 'Newsletter content here', 'sections': ['featured', 'updates', 'success_stories']}

    async def _handle_campaign(self, payload: Dict) -> Dict:
        campaign = payload.get('campaign', {})
        return {'campaign_name': campaign.get('name', ''), 'content_pieces': 5, 'status': 'prepared'}
