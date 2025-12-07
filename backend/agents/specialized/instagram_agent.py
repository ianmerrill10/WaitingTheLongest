#!/usr/bin/env python3
"""
===============================================================================
Instagram Agent - Instagram Content Creation & Management
===============================================================================
Creates and manages Instagram content for animal rescue promotion.

Features:
- Photo and video content creation
- Reels creation and management
- Stories management
- Hashtag optimization
- Carousel posts
- Engagement tracking
- Influencer collaboration

Cooperates with: Marketing, ImageProcessing, ContentWriter, Analytics
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
class InstagramPost:
    """Instagram post definition"""
    post_id: str
    post_type: str  # photo, video, carousel, reel, story
    media_paths: List[str]
    caption: str
    hashtags: List[str]
    location: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    status: str = "draft"
    metrics: Dict[str, int] = field(default_factory=lambda: {
        'likes': 0, 'comments': 0, 'saves': 0, 'shares': 0, 'reach': 0
    })


class InstagramAgent(CooperativeMixin, BaseAgent):
    """
    Instagram content creation and management agent.

    Commands:
    - create_post: Create an Instagram post
    - create_reel: Create an Instagram Reel
    - create_story: Create an Instagram Story
    - create_carousel: Create a carousel post
    - schedule_post: Schedule a post
    - get_hashtags: Get optimal hashtags
    - analyze_engagement: Analyze post engagement
    - get_performance: Get account performance
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="instagram",
            agent_name="Instagram Agent",
            agent_type="specialized_agent",
            description="Instagram content creation and management"
        )
        CooperativeMixin.__init__(self)

        self.posts: Dict[str, InstagramPost] = {}
        self.stories: List[Dict] = []
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN

        # Register cooperation handlers
        self.register_handler('create_content', self._handle_create_content)
        self.register_handler('start_campaign', self._handle_campaign)
        self.register_handler('get_performance', self._handle_performance_request)
        self.register_handler('post_animal', self._handle_post_animal)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute an Instagram task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "create_post":
                result = await self.create_post(task.payload)
            elif task.task_type == "create_reel":
                result = await self.create_reel(task.payload)
            elif task.task_type == "create_carousel":
                result = await self.create_carousel(task.payload)
            elif task.task_type == "get_hashtags":
                result = await self.get_optimal_hashtags(task.payload)
            elif task.task_type == "post_animal":
                result = await self.post_animal_content(task.payload)
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Instagram task completed: {task.task_type}",
                data=result,
                duration_seconds=(task.completed_at - task.started_at).total_seconds()
            )

        except Exception as e:
            self.logger.error(f"Instagram task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main Instagram agent loop"""
        self.logger.info("Instagram Agent starting")
        processed = 0

        while self.status.value == "running":
            await self.process_messages()

            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Instagram Agent completed", items_processed=processed)

    async def create_post(self, data: Dict) -> Dict:
        """Create an Instagram post"""
        animal_name = data.get('name', 'This sweetie')
        animal_type = data.get('type', 'dog')
        days_waiting = data.get('days_waiting', 0)
        image_path = data.get('image_path')

        # Request image processing if needed
        if not image_path and data.get('animal_id'):
            image_result = await self.request_from_agent(
                'image_processing',
                'get_animal_image',
                {'animal_id': data['animal_id'], 'format': 'instagram'}
            )
            image_path = image_result.get('image_path') if image_result else None

        # Generate caption
        caption = await self._generate_caption(animal_name, animal_type, days_waiting)

        # Get hashtags
        hashtags = await self.get_optimal_hashtags({
            'type': animal_type,
            'days_waiting': days_waiting
        })

        post = InstagramPost(
            post_id=f"ig_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            post_type='photo',
            media_paths=[image_path] if image_path else [],
            caption=caption,
            hashtags=hashtags['hashtags']
        )

        self.posts[post.post_id] = post

        return {
            'post_id': post.post_id,
            'caption': post.caption,
            'hashtags': post.hashtags,
            'status': 'created'
        }

    async def create_reel(self, data: Dict) -> Dict:
        """Create an Instagram Reel"""
        animal_id = data.get('animal_id')
        animal_name = data.get('name', 'This sweetie')
        days_waiting = data.get('days_waiting', 0)

        # Request video from Video Generator
        video_result = await self.request_from_agent(
            'video_generator',
            'create_short_video',
            {
                'animal_id': animal_id,
                'format': 'instagram_reel',
                'duration': 30,
                'style': 'dynamic'
            }
        )

        video_path = video_result.get('video_path') if video_result else None

        caption = await self._generate_caption(animal_name, 'dog', days_waiting, is_reel=True)

        post = InstagramPost(
            post_id=f"reel_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            post_type='reel',
            media_paths=[video_path] if video_path else [],
            caption=caption,
            hashtags=await self._get_reel_hashtags()
        )

        self.posts[post.post_id] = post

        return {
            'post_id': post.post_id,
            'type': 'reel',
            'video_path': video_path,
            'caption': caption
        }

    async def create_carousel(self, data: Dict) -> Dict:
        """Create a carousel post with multiple images"""
        images = data.get('images', [])
        animal_name = data.get('name', 'Meet our friend')
        story = data.get('story', '')

        # Process images through Image Processing agent
        processed_images = []
        for img in images:
            result = await self.request_from_agent(
                'image_processing',
                'optimize_for_instagram',
                {'image_path': img}
            )
            if result:
                processed_images.append(result.get('processed_path', img))

        caption = f"{story}\n\nSwipe to see more of {animal_name}! Every photo tells a story of hope."

        post = InstagramPost(
            post_id=f"carousel_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            post_type='carousel',
            media_paths=processed_images,
            caption=caption,
            hashtags=await self._get_carousel_hashtags()
        )

        self.posts[post.post_id] = post

        return {
            'post_id': post.post_id,
            'type': 'carousel',
            'image_count': len(processed_images),
            'caption': caption
        }

    async def _generate_caption(self, name: str, animal_type: str, days_waiting: int, is_reel: bool = False) -> str:
        """Generate Instagram caption"""
        if days_waiting > 365:
            years = days_waiting // 365
            intro = f"{name} has been waiting over {years} year{'s' if years > 1 else ''} for their forever home."
            cta = "Will you be the one to end their wait?"
        elif days_waiting > 180:
            intro = f"{days_waiting} days. That's how long {name} has been dreaming of a family."
            cta = "Could you be the one they've been waiting for?"
        elif days_waiting > 90:
            intro = f"{name} has been patiently waiting for {days_waiting} days."
            cta = "This perfect companion is ready to meet you!"
        else:
            intro = f"Meet {name}! This adorable {animal_type} is looking for their forever family."
            cta = "DM us to learn more about adoption!"

        if is_reel:
            return f"{intro} {cta}\n\n#waitingthelongest #adoptdontshop"
        else:
            return f"{intro}\n\n{cta}\n\nLink in bio to learn more about {name} and all our waiting pets."

    async def get_optimal_hashtags(self, data: Dict) -> Dict:
        """Get optimal hashtags for maximum reach"""
        animal_type = data.get('type', 'dog')
        days_waiting = data.get('days_waiting', 0)

        hashtags = [
            '#adoptdontshop', '#rescuedog', '#shelterpets', '#waitingthelongest',
            '#adoptme', '#rescuedogsofinstagram', '#shelterdogsofinstagram',
            '#dogsofinstagram', '#adoptadog', '#fosteringsaveslives'
        ]

        if animal_type == 'dog':
            hashtags.extend(['#dogstagram', '#instadog', '#doglover', '#dogoftheday'])
        elif animal_type == 'cat':
            hashtags.extend(['#catstagram', '#instacat', '#catlover', '#catoftheday'])

        if days_waiting > 180:
            hashtags.extend(['#overlooked', '#longstay', '#forgottenpets', '#pleaseadoptme'])

        return {'hashtags': hashtags[:30]}  # Instagram limit

    async def _get_reel_hashtags(self) -> List[str]:
        """Get hashtags optimized for Reels"""
        return [
            '#reels', '#reelsinstagram', '#reelsvideo', '#viralreels',
            '#adoptdontshop', '#rescuedog', '#waitingthelongest', '#shelterpets'
        ]

    async def _get_carousel_hashtags(self) -> List[str]:
        """Get hashtags for carousel posts"""
        return [
            '#adoptdontshop', '#rescuedog', '#shelterpets', '#dogsofinstagram',
            '#waitingthelongest', '#adoptme', '#rescuedogsofinstagram'
        ]

    async def post_animal_content(self, data: Dict) -> Dict:
        """Create content for a specific animal"""
        content_type = data.get('content_type', 'post')

        if content_type == 'reel':
            return await self.create_reel(data)
        elif content_type == 'carousel':
            return await self.create_carousel(data)
        else:
            return await self.create_post(data)

    async def _handle_create_content(self, payload: Dict) -> Dict:
        """Handle content creation requests"""
        return await self.post_animal_content(payload)

    async def _handle_campaign(self, payload: Dict) -> Dict:
        """Handle campaign start from Marketing agent"""
        campaign_id = payload.get('campaign_id')
        content_list = payload.get('content', [])

        created = []
        for content in content_list:
            result = await self.post_animal_content(content)
            created.append(result['post_id'])

        return {'campaign_id': campaign_id, 'created_posts': created}

    async def _handle_performance_request(self, payload: Dict) -> Dict:
        """Handle performance data requests"""
        total_reach = sum(p.metrics['reach'] for p in self.posts.values())
        total_likes = sum(p.metrics['likes'] for p in self.posts.values())
        total_saves = sum(p.metrics['saves'] for p in self.posts.values())

        return {
            'platform': 'instagram',
            'total_posts': len(self.posts),
            'total_reach': total_reach,
            'total_likes': total_likes,
            'total_saves': total_saves,
            'engagement_rate': (total_likes + total_saves) / max(total_reach, 1) * 100
        }

    async def _handle_post_animal(self, payload: Dict) -> Dict:
        """Handle animal posting requests from other agents"""
        return await self.post_animal_content(payload)


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Instagram Agent CLI")
    parser.add_argument('--post', action='store_true', help='Create sample post')
    parser.add_argument('--reel', action='store_true', help='Create sample reel')
    parser.add_argument('--hashtags', type=str, default='dog', help='Get hashtags for animal type')

    args = parser.parse_args()
    agent = InstagramAgent()

    if args.post:
        result = asyncio.run(agent.create_post({
            'name': 'Bella',
            'type': 'dog',
            'days_waiting': 200
        }))
        print(json.dumps(result, indent=2))
    elif args.reel:
        result = asyncio.run(agent.create_reel({
            'name': 'Max',
            'days_waiting': 365
        }))
        print(json.dumps(result, indent=2))
    elif args.hashtags:
        result = asyncio.run(agent.get_optimal_hashtags({'type': args.hashtags}))
        print(json.dumps(result, indent=2))
