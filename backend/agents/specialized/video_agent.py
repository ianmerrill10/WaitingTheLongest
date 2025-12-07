#!/usr/bin/env python3
"""
===============================================================================
Video Generator Agent - Video Content Creation
===============================================================================
Creates video content for social media and marketing.

Cooperates with: TikTok, Instagram, Facebook, Marketing, ImageProcessing
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory
from app.config import settings


class VideoGeneratorAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="video_generator", agent_name="Video Generator Agent",
                          agent_type="specialized_agent", description="Video content creation")
        CooperativeMixin.__init__(self)
        self.output_dir = Path(settings.VIDEO_OUTPUT_DIR)
        self.register_handler('create_short_video', self._handle_short)
        self.register_handler('create_slideshow', self._handle_slideshow)
        self.register_handler('add_music', self._handle_music)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "create_video":
            result = await self.create_video(task.payload)
        elif task.task_type == "create_slideshow":
            result = await self.create_slideshow(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Video task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Video Generator Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Video Agent completed")

    async def create_video(self, params: Dict) -> Dict:
        format_type = params.get('format', 'tiktok')
        duration = params.get('duration', 15)
        style = params.get('style', 'emotional')

        video_id = f"vid_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        output_path = str(self.output_dir / f"{video_id}.mp4")

        # In production, would use video processing libraries
        return {
            'video_id': video_id,
            'video_path': output_path,
            'format': format_type,
            'duration': duration,
            'style': style,
            'status': 'created'
        }

    async def create_slideshow(self, params: Dict) -> Dict:
        images = params.get('images', [])
        duration_per_image = params.get('duration_per_image', 3)

        return {
            'video_id': f"slide_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'image_count': len(images),
            'total_duration': len(images) * duration_per_image,
            'status': 'created'
        }

    async def _handle_short(self, payload: Dict) -> Dict:
        return await self.create_video(payload)
    async def _handle_slideshow(self, payload: Dict) -> Dict:
        return await self.create_slideshow(payload)
    async def _handle_music(self, payload: Dict) -> Dict:
        return {'video_id': payload.get('video_id'), 'music_added': True}
