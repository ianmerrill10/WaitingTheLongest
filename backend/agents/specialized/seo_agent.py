#!/usr/bin/env python3
"""
===============================================================================
SEO Agent - Search Engine Optimization
===============================================================================
Optimizes content for search engines and monitors SEO performance.

Features:
- Keyword research and optimization
- Meta tag generation
- Content SEO analysis
- Sitemap management
- Search ranking monitoring
- Backlink tracking
- Schema markup generation

Cooperates with: ContentWriter, Marketing, Analytics
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


class SEOAgent(CooperativeMixin, BaseAgent):
    """SEO optimization agent."""

    def __init__(self):
        BaseAgent.__init__(self, agent_id="seo", agent_name="SEO Agent",
                          agent_type="specialized_agent", description="Search engine optimization")
        CooperativeMixin.__init__(self)
        self.keywords: Dict[str, Dict] = {}
        self.register_handler('get_keywords', self._handle_keywords)
        self.register_handler('analyze_content', self._handle_analyze)
        self.register_handler('generate_meta', self._handle_meta)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        task.started_at = datetime.now()
        if task.task_type == "keyword_research":
            result = await self.keyword_research(task.payload)
        elif task.task_type == "analyze_content":
            result = await self.analyze_content(task.payload)
        elif task.task_type == "generate_meta":
            result = await self.generate_meta(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        task.completed_at = datetime.now()
        return AgentResult(success=True, message="SEO task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("SEO Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="SEO Agent completed")

    async def keyword_research(self, params: Dict) -> Dict:
        topic = params.get('topic', 'dog adoption')
        keywords = {
            'primary': [f'{topic}', f'{topic} near me', f'adopt a {topic.split()[0]}'],
            'secondary': ['rescue dogs', 'shelter pets', 'adopt don\'t shop', 'pet adoption'],
            'long_tail': [f'how to adopt a {topic.split()[0]}', f'{topic} process', f'best {topic.split()[0]} breeds to adopt'],
            'local': [f'{topic} [city]', f'{topic} [state]', 'animal shelters near me']
        }
        return {'topic': topic, 'keywords': keywords}

    async def analyze_content(self, params: Dict) -> Dict:
        content = params.get('content', '')
        word_count = len(content.split())
        return {
            'word_count': word_count,
            'score': min(100, word_count // 10),
            'recommendations': [
                'Add more keywords naturally',
                'Include internal links',
                'Add alt text to images'
            ] if word_count < 300 else ['Good content length']
        }

    async def generate_meta(self, params: Dict) -> Dict:
        title = params.get('title', '')
        description = params.get('description', '')
        return {
            'meta_title': f"{title} | Waiting The Longest"[:60],
            'meta_description': description[:155] + '...' if len(description) > 155 else description,
            'og_title': title,
            'og_description': description[:200],
            'schema': {'@type': 'WebPage', 'name': title}
        }

    async def _handle_keywords(self, payload: Dict) -> Dict:
        return await self.keyword_research(payload)

    async def _handle_analyze(self, payload: Dict) -> Dict:
        return await self.analyze_content(payload)

    async def _handle_meta(self, payload: Dict) -> Dict:
        return await self.generate_meta(payload)
