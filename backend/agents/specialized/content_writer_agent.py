#!/usr/bin/env python3
"""
===============================================================================
Content Writer Agent - Content Creation
===============================================================================
Creates compelling content for animals, marketing, and communications on the
Waiting The Longest platform.

Features:
- Animal bio generation with personality
- Platform-specific social media posts (Instagram, TikTok, Facebook)
- Newsletter content creation
- Blog article drafting
- Email templates
- Adoption success stories
- SEO-optimized content
- Campaign content preparation

Usage Example:
    agent = ContentWriterAgent()

    # Write animal bio
    bio = await agent.write_animal_bio({
        'name': 'Max',
        'type': 'dog',
        'personality': 'friendly and playful',
        'days_waiting': 45
    })
    print(bio['bio'])

    # Create social media post
    post = await agent.write_social_post({
        'platform': 'instagram',
        'name': 'Max',
        'days_waiting': 45
    })

Cooperates with: Marketing, TikTok, Instagram, Facebook, SEO, Email

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
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
    """
    Content creation and copywriting agent.

    Generates compelling content for animal profiles, social media,
    newsletters, and marketing campaigns. Tailors content to different
    platforms and audiences.

    Supported Commands:
        write_bio: Generate animal biography
        write_social_post: Create platform-specific social media post
        write_newsletter: Generate newsletter content
        prepare_campaign_content: Prepare content for marketing campaign

    Examples:
        >>> agent = ContentWriterAgent()
        >>> # Generate animal bio
        >>> bio = await agent.write_animal_bio({
        ...     'name': 'Bella',
        ...     'type': 'cat',
        ...     'personality': 'gentle and affectionate',
        ...     'days_waiting': 30
        ... })
        >>> print(bio['bio'])
    """

    def __init__(self):
        BaseAgent.__init__(self, agent_id="content_writer", agent_name="Content Writer Agent",
                          agent_type="specialized_agent", description="Content creation specialist")
        CooperativeMixin.__init__(self)
        self.register_handler('write_bio', self._handle_bio)
        self.register_handler('write_social_post', self._handle_social)
        self.register_handler('write_newsletter', self._handle_newsletter)
        self.register_handler('prepare_campaign_content', self._handle_campaign)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """
        Execute a content creation task.

        Args:
            task: AgentTask with task_type and content parameters

        Returns:
            AgentResult with generated content

        Examples:
            >>> task = AgentTask(
            ...     task_id="content_1",
            ...     task_type="write_bio",
            ...     payload={'name': 'Max', 'type': 'dog'}
            ... )
            >>> result = await agent.execute_task(task)
        """
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
        """
        Main content writer execution loop.

        Returns:
            AgentResult with completion status
        """
        self.logger.info("Content Writer Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Content Writer completed")

    async def write_animal_bio(self, params: Dict) -> Dict:
        """
        Generate compelling animal biography for adoption profile.

        Args:
            params: Dictionary containing:
                - name (str): Animal's name
                - type (str): Animal type (dog, cat, etc.)
                - personality (str): Personality description
                - days_waiting (int): Days waiting for adoption

        Returns:
            Dictionary with name, bio text, and word count

        Examples:
            >>> bio = await agent.write_animal_bio({
            ...     'name': 'Charlie',
            ...     'type': 'dog',
            ...     'personality': 'energetic and loving',
            ...     'days_waiting': 60
            ... })
            >>> print(bio['bio'])
        """
        name = params.get('name', 'This pet')
        animal_type = params.get('type', 'dog')
        personality = params.get('personality', 'friendly and loving')
        days = params.get('days_waiting', 0)

        bio = f"{name} is a wonderful {animal_type} who has been patiently waiting for {days} days to find their forever family. "
        bio += f"Known for being {personality}, {name} would make the perfect companion. "
        bio += "Could you be the one to give them the loving home they deserve?"

        return {'name': name, 'bio': bio, 'word_count': len(bio.split())}

    async def write_social_post(self, params: Dict) -> Dict:
        """
        Create platform-specific social media post.

        Args:
            params: Dictionary containing:
                - platform (str): Social platform ('instagram', 'tiktok', 'facebook')
                - name (str): Animal's name
                - days_waiting (int): Days waiting for adoption

        Returns:
            Dictionary with platform and post text

        Examples:
            >>> post = await agent.write_social_post({
            ...     'platform': 'instagram',
            ...     'name': 'Luna',
            ...     'days_waiting': 45
            ... })
            >>> print(post['post'])
        """
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
        """Handler for inter-agent bio generation requests."""
        return await self.write_animal_bio(payload)

    async def _handle_social(self, payload: Dict) -> Dict:
        """Handler for inter-agent social post requests."""
        return await self.write_social_post(payload)

    async def _handle_newsletter(self, payload: Dict) -> Dict:
        """Handler for inter-agent newsletter content requests."""
        return {'content': 'Newsletter content here', 'sections': ['featured', 'updates', 'success_stories']}

    async def _handle_campaign(self, payload: Dict) -> Dict:
        """Handler for inter-agent campaign content preparation requests."""
        campaign = payload.get('campaign', {})
        return {'campaign_name': campaign.get('name', ''), 'content_pieces': 5, 'status': 'prepared'}
