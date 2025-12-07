#!/usr/bin/env python3
"""
===============================================================================
Facebook Agent - Facebook Content Creation & Management
===============================================================================
Creates and manages Facebook content for animal rescue promotion.

Features:
- Post creation and scheduling
- Event management
- Group posting
- Fundraiser management
- Facebook Live coordination
- Ad campaign management
- Messenger bot integration

Cooperates with: Marketing, ContentWriter, Analytics, DonationTracker
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority
from agents.protocols import CooperativeMixin, DataCategory, Priority
from app.config import settings


@dataclass
class FacebookPost:
    """Facebook post definition"""
    post_id: str
    post_type: str  # text, photo, video, link, event
    content: str
    media_paths: List[str] = field(default_factory=list)
    link: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    status: str = "draft"
    target_audience: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, int] = field(default_factory=lambda: {
        'reach': 0, 'reactions': 0, 'comments': 0, 'shares': 0, 'clicks': 0
    })


class FacebookAgent(CooperativeMixin, BaseAgent):
    """
    Facebook content creation and management agent.

    Commands:
    - create_post: Create a Facebook post
    - create_event: Create a Facebook event
    - schedule_post: Schedule a post
    - create_fundraiser: Create a fundraiser
    - boost_post: Boost a post with ads
    - get_performance: Get page performance
    - respond_comments: Handle comment responses
    - post_to_group: Post to a Facebook group
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="facebook",
            agent_name="Facebook Agent",
            agent_type="specialized_agent",
            description="Facebook content creation and management"
        )
        CooperativeMixin.__init__(self)

        self.posts: Dict[str, FacebookPost] = {}
        self.events: List[Dict] = []
        self.fundraisers: List[Dict] = []
        self.page_token = settings.FACEBOOK_PAGE_TOKEN

        # Register cooperation handlers
        self.register_handler('create_content', self._handle_create_content)
        self.register_handler('start_campaign', self._handle_campaign)
        self.register_handler('get_performance', self._handle_performance_request)
        self.register_handler('create_event', self._handle_create_event)
        self.register_handler('create_fundraiser', self._handle_create_fundraiser)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a Facebook task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "create_post":
                result = await self.create_post(task.payload)
            elif task.task_type == "create_event":
                result = await self.create_event(task.payload)
            elif task.task_type == "create_fundraiser":
                result = await self.create_fundraiser(task.payload)
            elif task.task_type == "post_animal":
                result = await self.post_animal_content(task.payload)
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Facebook task completed: {task.task_type}",
                data=result,
                duration_seconds=(task.completed_at - task.started_at).total_seconds()
            )

        except Exception as e:
            self.logger.error(f"Facebook task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main Facebook agent loop"""
        self.logger.info("Facebook Agent starting")
        processed = 0

        while self.status.value == "running":
            await self.process_messages()

            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Facebook Agent completed", items_processed=processed)

    async def create_post(self, data: Dict) -> Dict:
        """Create a Facebook post"""
        animal_name = data.get('name', 'This sweetie')
        animal_type = data.get('type', 'dog')
        days_waiting = data.get('days_waiting', 0)
        image_path = data.get('image_path')
        shelter_name = data.get('shelter_name', 'our partner shelter')

        # Generate compelling Facebook content (longer form than other platforms)
        content = await self._generate_content(animal_name, animal_type, days_waiting, shelter_name)

        post = FacebookPost(
            post_id=f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            post_type='photo' if image_path else 'text',
            content=content,
            media_paths=[image_path] if image_path else []
        )

        self.posts[post.post_id] = post

        # Share discovery with Marketing
        self.share_discovery(
            DataCategory.CONTENT,
            f"New Facebook post created for {animal_name}",
            {'post_id': post.post_id, 'content': content},
            tags=['facebook', 'post', animal_type]
        )

        return {
            'post_id': post.post_id,
            'content': content,
            'status': 'created'
        }

    async def _generate_content(self, name: str, animal_type: str, days_waiting: int, shelter: str) -> str:
        """Generate Facebook post content"""
        if days_waiting > 365:
            years = days_waiting // 365
            intro = f"PLEASE SHARE: {name} has been waiting for over {years} year{'s' if years > 1 else ''}"
            body = f"Every day, {name} watches other animals leave with their new families. Every day, {name} waits and hopes. After {days_waiting} days at {shelter}, this beautiful {animal_type} is still searching for someone to call their own."
            cta = f"Will you be the one to give {name} the forever home they deserve? Even if you can't adopt, a share could help {name} find their perfect match."
        elif days_waiting > 180:
            intro = f"OVERLOOKED BUT NOT FORGOTTEN: Meet {name}"
            body = f"For {days_waiting} days, {name} has been at {shelter}, waiting for their chance at happiness. This incredible {animal_type} has so much love to give!"
            cta = "Share to help spread the word - together we can find {name} their forever family."
        else:
            intro = f"MEET {name.upper()}! New Friend Available for Adoption"
            body = f"This adorable {animal_type} is looking for a loving home! {name} is currently at {shelter} and ready to meet their perfect match."
            cta = "Comment below if you'd like to learn more about adoption!"

        hashtags = "#adoptdontshop #rescuedog #shelterpets #waitingthelongest"

        return f"{intro}\n\n{body}\n\n{cta}\n\n{hashtags}"

    async def create_event(self, data: Dict) -> Dict:
        """Create a Facebook event for adoption day or shelter visit"""
        event = {
            'event_id': f"event_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'name': data.get('name', 'Adoption Event'),
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'start_time': data.get('start_time'),
            'end_time': data.get('end_time'),
            'status': 'created'
        }

        self.events.append(event)

        return event

    async def create_fundraiser(self, data: Dict) -> Dict:
        """Create a Facebook fundraiser for a shelter or animal"""
        fundraiser = {
            'fundraiser_id': f"fund_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'title': data.get('title', 'Help Our Shelter'),
            'goal': data.get('goal', 1000),
            'description': data.get('description', ''),
            'beneficiary': data.get('beneficiary', 'shelter'),
            'status': 'active',
            'raised': 0
        }

        self.fundraisers.append(fundraiser)

        # Notify Donation Tracker agent
        self.handoff_to_agent(
            'donation_tracker',
            'track_fundraiser',
            f'Track Facebook fundraiser: {fundraiser["title"]}',
            {'fundraiser': fundraiser}
        )

        return fundraiser

    async def post_animal_content(self, data: Dict) -> Dict:
        """Create comprehensive content for an animal"""
        # Request additional info from Librarian if available
        if data.get('animal_id') and not data.get('full_profile'):
            animal_info = await self.request_from_agent(
                'librarian',
                'get_animal_profile',
                {'animal_id': data['animal_id']}
            )
            if animal_info:
                data.update(animal_info)

        return await self.create_post(data)

    async def _handle_create_content(self, payload: Dict) -> Dict:
        """Handle content creation requests from other agents"""
        return await self.create_post(payload)

    async def _handle_campaign(self, payload: Dict) -> Dict:
        """Handle campaign start from Marketing agent"""
        campaign_id = payload.get('campaign_id')
        content_list = payload.get('content', [])

        created = []
        for content in content_list:
            result = await self.create_post(content)
            created.append(result['post_id'])

        return {'campaign_id': campaign_id, 'created_posts': created}

    async def _handle_performance_request(self, payload: Dict) -> Dict:
        """Handle performance data requests"""
        total_reach = sum(p.metrics['reach'] for p in self.posts.values())
        total_reactions = sum(p.metrics['reactions'] for p in self.posts.values())
        total_shares = sum(p.metrics['shares'] for p in self.posts.values())

        return {
            'platform': 'facebook',
            'total_posts': len(self.posts),
            'total_events': len(self.events),
            'total_fundraisers': len(self.fundraisers),
            'total_reach': total_reach,
            'total_reactions': total_reactions,
            'total_shares': total_shares,
            'engagement_rate': (total_reactions + total_shares) / max(total_reach, 1) * 100
        }

    async def _handle_create_event(self, payload: Dict) -> Dict:
        """Handle event creation requests"""
        return await self.create_event(payload)

    async def _handle_create_fundraiser(self, payload: Dict) -> Dict:
        """Handle fundraiser creation requests"""
        return await self.create_fundraiser(payload)


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Facebook Agent CLI")
    parser.add_argument('--post', action='store_true', help='Create sample post')
    parser.add_argument('--event', type=str, help='Create event with name')
    parser.add_argument('--fundraiser', type=str, help='Create fundraiser with title')

    args = parser.parse_args()
    agent = FacebookAgent()

    if args.post:
        result = asyncio.run(agent.create_post({
            'name': 'Charlie',
            'type': 'dog',
            'days_waiting': 400,
            'shelter_name': 'Happy Tails Rescue'
        }))
        print(json.dumps(result, indent=2))
    elif args.event:
        result = asyncio.run(agent.create_event({'name': args.event}))
        print(json.dumps(result, indent=2))
    elif args.fundraiser:
        result = asyncio.run(agent.create_fundraiser({'title': args.fundraiser, 'goal': 5000}))
        print(json.dumps(result, indent=2))
