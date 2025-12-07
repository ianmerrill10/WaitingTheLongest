#!/usr/bin/env python3
"""
===============================================================================
TikTok Agent - TikTok Content Creation & Management
===============================================================================
Creates and manages TikTok content for animal rescue promotion.

Features:
- Short-form video content creation
- Trend analysis and hashtag optimization
- Scheduled posting
- Engagement tracking
- Viral content detection
- Sound/music selection
- Caption generation

Cooperates with: Marketing, VideoGenerator, ContentWriter, Analytics
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
class TikTokPost:
    """TikTok post definition"""
    post_id: str
    video_path: str
    caption: str
    hashtags: List[str]
    sound: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    status: str = "draft"
    metrics: Dict[str, int] = field(default_factory=lambda: {
        'views': 0, 'likes': 0, 'comments': 0, 'shares': 0
    })


class TikTokAgent(CooperativeMixin, BaseAgent):
    """
    TikTok content creation and management agent.

    Commands:
    - create_video: Create a TikTok video for an animal
    - schedule_post: Schedule a TikTok post
    - get_trends: Get current TikTok trends
    - analyze_hashtags: Analyze hashtag performance
    - get_performance: Get account/post performance
    - generate_caption: Generate engaging caption
    - find_sounds: Find trending sounds for content
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="tiktok",
            agent_name="TikTok Agent",
            agent_type="specialized_agent",
            description="TikTok content creation and management"
        )
        CooperativeMixin.__init__(self)

        self.posts: Dict[str, TikTokPost] = {}
        self.trending_hashtags: List[str] = []
        self.trending_sounds: List[Dict] = []
        self.access_token = settings.TIKTOK_ACCESS_TOKEN

        # Register cooperation handlers
        self.register_handler('create_content', self._handle_create_content)
        self.register_handler('start_campaign', self._handle_campaign)
        self.register_handler('get_performance', self._handle_performance_request)
        self.register_handler('get_trends', self._handle_trends_request)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a TikTok task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "create_video":
                result = await self.create_video(task.payload)
            elif task.task_type == "schedule_post":
                result = await self.schedule_post(task.payload)
            elif task.task_type == "get_trends":
                result = await self.get_trends()
            elif task.task_type == "generate_caption":
                result = await self.generate_caption(task.payload)
            elif task.task_type == "post_animal":
                result = await self.post_animal_content(task.payload)
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"TikTok task completed: {task.task_type}",
                data=result,
                duration_seconds=(task.completed_at - task.started_at).total_seconds()
            )

        except Exception as e:
            self.logger.error(f"TikTok task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main TikTok agent loop"""
        self.logger.info("TikTok Agent starting")
        processed = 0

        while self.status.value == "running":
            await self.process_messages()

            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="TikTok Agent completed", items_processed=processed)

    async def create_video(self, data: Dict) -> Dict:
        """Create a TikTok video for an animal"""
        animal_id = data.get('animal_id')
        animal_name = data.get('name', 'This sweetie')
        animal_type = data.get('type', 'dog')
        days_waiting = data.get('days_waiting', 0)

        # Request video generation from Video Generator agent
        video_result = await self.request_from_agent(
            'video_generator',
            'create_short_video',
            {
                'animal_id': animal_id,
                'format': 'tiktok',
                'duration': 15,
                'style': 'emotional',
                'music': True
            }
        )

        video_path = video_result.get('video_path') if video_result else None

        # Generate caption
        caption = await self.generate_caption({
            'name': animal_name,
            'type': animal_type,
            'days_waiting': days_waiting
        })

        # Get optimal hashtags
        hashtags = await self._get_optimal_hashtags(animal_type, days_waiting)

        post = TikTokPost(
            post_id=f"tt_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            video_path=video_path or '',
            caption=caption['caption'],
            hashtags=hashtags
        )

        self.posts[post.post_id] = post

        return {
            'post_id': post.post_id,
            'video_path': post.video_path,
            'caption': post.caption,
            'hashtags': post.hashtags
        }

    async def generate_caption(self, data: Dict) -> Dict:
        """Generate an engaging TikTok caption"""
        name = data.get('name', 'This sweetie')
        animal_type = data.get('type', 'dog')
        days_waiting = data.get('days_waiting', 0)

        # Emotional hooks based on waiting time
        if days_waiting > 365:
            hook = f"{name} has waited over a YEAR for a family"
            emotion = "heartbreaking"
        elif days_waiting > 180:
            hook = f"{name} has been waiting {days_waiting} days"
            emotion = "urgent"
        elif days_waiting > 90:
            hook = f"3 months and still waiting..."
            emotion = "hopeful"
        else:
            hook = f"Meet {name}!"
            emotion = "exciting"

        captions = {
            'heartbreaking': f"{hook} 💔 Every day matters. Will you be their forever? #adoptdontshop #waitingthelongest",
            'urgent': f"{hook}. That's {days_waiting} days of hoping. {days_waiting} days of waiting. Please share 🙏",
            'hopeful': f"{hook} but never gives up hope! Could you be the one? 🏠❤️",
            'exciting': f"{hook} This {animal_type} is ready to steal your heart! 🐾✨"
        }

        return {
            'caption': captions[emotion],
            'emotion': emotion,
            'hook': hook
        }

    async def _get_optimal_hashtags(self, animal_type: str, days_waiting: int) -> List[str]:
        """Get optimal hashtags for maximum reach"""
        base_hashtags = [
            '#adoptdontshop', '#rescuedog', '#shelterpets',
            '#waitingthelongest', '#adoptme', '#fyp', '#foryou'
        ]

        if animal_type == 'dog':
            base_hashtags.extend(['#dogsoftiktok', '#rescuedogsoftiktok', '#dogadoption'])
        elif animal_type == 'cat':
            base_hashtags.extend(['#catsoftiktok', '#rescuecats', '#catadoption'])

        if days_waiting > 365:
            base_hashtags.extend(['#longstay', '#overlooked', '#seniordog'])
        elif days_waiting > 180:
            base_hashtags.extend(['#waitingforhome', '#pleaseadoptme'])

        return base_hashtags[:15]  # TikTok limit

    async def get_trends(self) -> Dict:
        """Get current TikTok trends"""
        # In production, this would call TikTok API
        trending = {
            'hashtags': [
                '#adoptdontshop', '#rescuedog', '#shelterpets',
                '#dogsoftiktok', '#petadoption', '#fyp'
            ],
            'sounds': [
                {'name': 'Emotional Piano', 'id': 'sound_001'},
                {'name': 'Happy Upbeat', 'id': 'sound_002'},
                {'name': 'Heartfelt Acoustic', 'id': 'sound_003'}
            ],
            'formats': [
                'Before/After adoption glow-up',
                'Day in the life at shelter',
                'Meet the longest resident',
                'Success story reunion'
            ]
        }

        self.trending_hashtags = trending['hashtags']
        self.trending_sounds = trending['sounds']

        return trending

    async def schedule_post(self, data: Dict) -> Dict:
        """Schedule a TikTok post"""
        post_id = data.get('post_id')
        schedule_time = datetime.fromisoformat(data['schedule_time'])

        if post_id in self.posts:
            self.posts[post_id].scheduled_time = schedule_time
            self.posts[post_id].status = 'scheduled'

            return {
                'post_id': post_id,
                'scheduled_time': schedule_time.isoformat(),
                'status': 'scheduled'
            }

        return {'error': 'Post not found'}

    async def post_animal_content(self, data: Dict) -> Dict:
        """Create and post content for a specific animal"""
        # Request animal details from Librarian if needed
        animal_data = data
        if 'animal_id' in data and 'name' not in data:
            animal_data = await self.request_from_agent(
                'librarian',
                'get_animal',
                {'animal_id': data['animal_id']}
            ) or data

        # Create the video content
        video_result = await self.create_video(animal_data)

        # Share the content creation with Marketing agent
        self.share_discovery(
            DataCategory.CONTENT,
            f"New TikTok content created",
            video_result,
            tags=['tiktok', 'video', 'animal']
        )

        return video_result

    async def _handle_create_content(self, payload: Dict) -> Dict:
        """Handle content creation requests"""
        return await self.create_video(payload)

    async def _handle_campaign(self, payload: Dict) -> Dict:
        """Handle campaign start requests from Marketing agent"""
        campaign_id = payload.get('campaign_id')
        content_list = payload.get('content', [])

        scheduled = []
        for i, content in enumerate(content_list):
            schedule_time = datetime.now() + timedelta(days=i)
            result = await self.create_video(content)
            await self.schedule_post({
                'post_id': result['post_id'],
                'schedule_time': schedule_time.isoformat()
            })
            scheduled.append(result['post_id'])

        return {'campaign_id': campaign_id, 'scheduled_posts': scheduled}

    async def _handle_performance_request(self, payload: Dict) -> Dict:
        """Handle performance data requests"""
        campaign_id = payload.get('campaign_id')

        total_views = sum(p.metrics['views'] for p in self.posts.values())
        total_likes = sum(p.metrics['likes'] for p in self.posts.values())
        total_shares = sum(p.metrics['shares'] for p in self.posts.values())

        return {
            'platform': 'tiktok',
            'total_posts': len(self.posts),
            'total_views': total_views,
            'total_likes': total_likes,
            'total_shares': total_shares,
            'engagement_rate': (total_likes + total_shares) / max(total_views, 1) * 100
        }

    async def _handle_trends_request(self, payload: Dict) -> Dict:
        """Handle trend data requests"""
        return await self.get_trends()


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="TikTok Agent CLI")
    parser.add_argument('--create', action='store_true', help='Create sample video')
    parser.add_argument('--trends', action='store_true', help='Get current trends')
    parser.add_argument('--caption', type=str, help='Generate caption for animal name')

    args = parser.parse_args()
    agent = TikTokAgent()

    if args.create:
        result = asyncio.run(agent.create_video({
            'name': 'Buddy',
            'type': 'dog',
            'days_waiting': 180
        }))
        print(json.dumps(result, indent=2))
    elif args.trends:
        result = asyncio.run(agent.get_trends())
        print(json.dumps(result, indent=2))
    elif args.caption:
        result = asyncio.run(agent.generate_caption({'name': args.caption}))
        print(json.dumps(result, indent=2))
