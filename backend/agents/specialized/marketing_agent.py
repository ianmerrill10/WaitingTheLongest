#!/usr/bin/env python3
"""
===============================================================================
Marketing Agent - Strategic Marketing Campaign Manager
===============================================================================
Orchestrates marketing campaigns across all channels, coordinates with social
media agents, and manages promotional content.

Features:
- Campaign planning and execution
- Content calendar management
- Performance tracking across channels
- A/B testing coordination
- Trend analysis and recommendations
- Cross-platform campaign synchronization

Cooperates with: TikTok, Instagram, Facebook, ContentWriter, Analytics, SEO
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


@dataclass
class Campaign:
    """Marketing campaign definition"""
    campaign_id: str
    name: str
    objective: str  # awareness, engagement, conversions
    channels: List[str]  # tiktok, instagram, facebook, email
    start_date: datetime
    end_date: datetime
    budget: float = 0.0
    target_audience: Dict[str, Any] = field(default_factory=dict)
    content_pieces: List[Dict] = field(default_factory=list)
    status: str = "draft"  # draft, active, paused, completed
    metrics: Dict[str, Any] = field(default_factory=dict)


class MarketingAgent(CooperativeMixin, BaseAgent):
    """
    Strategic marketing agent that coordinates all marketing efforts.

    Commands:
    - create_campaign: Create a new marketing campaign
    - launch_campaign: Activate a campaign
    - pause_campaign: Pause an active campaign
    - analyze_performance: Get campaign performance metrics
    - suggest_content: Generate content suggestions
    - schedule_posts: Schedule social media posts
    - find_trending: Find trending topics for content
    - generate_report: Generate marketing report
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="marketing",
            agent_name="Marketing Agent",
            agent_type="specialized_agent",
            description="Strategic marketing campaign manager"
        )
        CooperativeMixin.__init__(self)

        self.campaigns: Dict[str, Campaign] = {}
        self.content_calendar: List[Dict] = []
        self.performance_history: List[Dict] = []

        # Register handlers for cooperation
        self.register_handler('get_active_campaigns', self._handle_campaign_request)
        self.register_handler('content_suggestion', self._handle_content_suggestion)
        self.register_handler('schedule_content', self._handle_schedule_content)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a marketing task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "create_campaign":
                result = await self.create_campaign(task.payload)
            elif task.task_type == "launch_campaign":
                result = await self.launch_campaign(task.payload.get('campaign_id'))
            elif task.task_type == "analyze_performance":
                result = await self.analyze_performance(task.payload.get('campaign_id'))
            elif task.task_type == "suggest_content":
                result = await self.suggest_content(task.payload)
            elif task.task_type == "daily_marketing":
                result = await self.run_daily_marketing()
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            task.status = "completed"

            return AgentResult(
                success=True,
                message=f"Marketing task completed: {task.task_type}",
                data=result,
                duration_seconds=(task.completed_at - task.started_at).total_seconds()
            )

        except Exception as e:
            self.logger.error(f"Marketing task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main marketing agent loop"""
        self.logger.info("Marketing Agent starting")
        processed = 0

        while self.status.value == "running":
            # Process messages from other agents
            await self.process_messages()

            # Process queued tasks
            task = self.get_next_task()
            if task:
                result = await self.execute_task(task)
                self.completed_tasks.append(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(
            success=True,
            message="Marketing Agent completed",
            items_processed=processed
        )

    async def create_campaign(self, data: Dict) -> Dict:
        """Create a new marketing campaign"""
        campaign = Campaign(
            campaign_id=f"campaign_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=data.get('name', 'Unnamed Campaign'),
            objective=data.get('objective', 'awareness'),
            channels=data.get('channels', ['instagram', 'facebook']),
            start_date=datetime.fromisoformat(data['start_date']) if 'start_date' in data else datetime.now(),
            end_date=datetime.fromisoformat(data['end_date']) if 'end_date' in data else datetime.now() + timedelta(days=30),
            budget=data.get('budget', 0),
            target_audience=data.get('target_audience', {})
        )

        self.campaigns[campaign.campaign_id] = campaign
        self.logger.info(f"Created campaign: {campaign.name}")

        # Notify content writer to prepare content
        self.handoff_to_agent(
            'content_writer',
            'prepare_campaign_content',
            f'Prepare content for campaign: {campaign.name}',
            {'campaign': campaign.__dict__, 'objective': campaign.objective}
        )

        return {'campaign_id': campaign.campaign_id, 'status': 'created'}

    async def launch_campaign(self, campaign_id: str) -> Dict:
        """Launch a marketing campaign across all channels"""
        if campaign_id not in self.campaigns:
            return {'error': 'Campaign not found'}

        campaign = self.campaigns[campaign_id]
        campaign.status = 'active'

        # Request each social media agent to start posting
        for channel in campaign.channels:
            if channel == 'tiktok':
                await self.request_from_agent('tiktok', 'start_campaign', {
                    'campaign_id': campaign_id,
                    'content': campaign.content_pieces
                })
            elif channel == 'instagram':
                await self.request_from_agent('instagram', 'start_campaign', {
                    'campaign_id': campaign_id,
                    'content': campaign.content_pieces
                })
            elif channel == 'facebook':
                await self.request_from_agent('facebook', 'start_campaign', {
                    'campaign_id': campaign_id,
                    'content': campaign.content_pieces
                })

        self.logger.info(f"Launched campaign: {campaign.name}")
        return {'campaign_id': campaign_id, 'status': 'active', 'channels': campaign.channels}

    async def analyze_performance(self, campaign_id: Optional[str] = None) -> Dict:
        """Analyze campaign performance"""
        # Request analytics from Analytics agent
        analytics_data = await self.request_from_agent(
            'analytics',
            'get_campaign_metrics',
            {'campaign_id': campaign_id}
        )

        # Request social performance from each platform
        platforms = {}
        for platform in ['tiktok', 'instagram', 'facebook']:
            data = await self.request_from_agent(
                platform,
                'get_performance',
                {'campaign_id': campaign_id}
            )
            if data:
                platforms[platform] = data

        return {
            'campaign_id': campaign_id,
            'analytics': analytics_data,
            'platforms': platforms,
            'analyzed_at': datetime.now().isoformat()
        }

    async def suggest_content(self, data: Dict) -> Dict:
        """Generate content suggestions based on trends and performance"""
        topic = data.get('topic', 'dog adoption')
        platform = data.get('platform', 'all')

        # Get trending topics from sentiment analysis
        trends = await self.request_from_agent(
            'sentiment_analysis',
            'get_trends',
            {'category': 'pets', 'platform': platform}
        )

        # Get SEO recommendations
        seo_data = await self.request_from_agent(
            'seo',
            'get_keywords',
            {'topic': topic}
        )

        suggestions = {
            'topic': topic,
            'trends': trends or [],
            'seo_keywords': seo_data or [],
            'content_ideas': [
                f"Heartwarming story of longest-waiting dog finding home",
                f"Tips for adopting senior dogs",
                f"Why shelter dogs make the best companions",
                f"Behind the scenes at local rescue",
                f"Success stories from adopters"
            ],
            'best_times': {
                'tiktok': ['6pm-9pm weekdays', '2pm-5pm weekends'],
                'instagram': ['11am-1pm', '7pm-9pm'],
                'facebook': ['1pm-4pm', '8pm-9pm']
            }
        }

        return suggestions

    async def run_daily_marketing(self) -> Dict:
        """Run daily marketing tasks"""
        results = {
            'date': datetime.now().isoformat(),
            'tasks_completed': []
        }

        # Check active campaigns
        active_campaigns = [c for c in self.campaigns.values() if c.status == 'active']
        results['active_campaigns'] = len(active_campaigns)

        # Get analytics for active campaigns
        for campaign in active_campaigns:
            perf = await self.analyze_performance(campaign.campaign_id)
            results['tasks_completed'].append(f"Analyzed {campaign.name}")

        # Share daily marketing data with interested agents
        self.share_discovery(
            DataCategory.MARKETING,
            'Daily Marketing Summary',
            results,
            tags=['daily', 'summary']
        )

        return results

    async def _handle_campaign_request(self, payload: Dict) -> Dict:
        """Handle requests for campaign information"""
        status_filter = payload.get('status', 'active')
        campaigns = [
            c.__dict__ for c in self.campaigns.values()
            if c.status == status_filter
        ]
        return {'campaigns': campaigns}

    async def _handle_content_suggestion(self, payload: Dict) -> Dict:
        """Handle content suggestion requests from other agents"""
        return await self.suggest_content(payload)

    async def _handle_schedule_content(self, payload: Dict) -> Dict:
        """Handle content scheduling requests"""
        content = payload.get('content')
        schedule_time = payload.get('schedule_time')
        platform = payload.get('platform')

        self.content_calendar.append({
            'content': content,
            'schedule_time': schedule_time,
            'platform': platform,
            'status': 'scheduled'
        })

        return {'scheduled': True, 'calendar_size': len(self.content_calendar)}


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Marketing Agent CLI")
    parser.add_argument('--create-campaign', type=str, help='Create campaign with name')
    parser.add_argument('--suggest', type=str, help='Get content suggestions for topic')
    parser.add_argument('--daily', action='store_true', help='Run daily marketing tasks')

    args = parser.parse_args()
    agent = MarketingAgent()

    if args.create_campaign:
        result = asyncio.run(agent.create_campaign({'name': args.create_campaign}))
        print(result)
    elif args.suggest:
        result = asyncio.run(agent.suggest_content({'topic': args.suggest}))
        print(result)
    elif args.daily:
        result = asyncio.run(agent.run_daily_marketing())
        print(result)
