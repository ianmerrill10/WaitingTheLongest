#!/usr/bin/env python3
"""
===============================================================================
Sentiment Analysis Agent - Social Sentiment Monitoring
===============================================================================
Analyzes sentiment from social media and user feedback.

Cooperates with: Marketing, Analytics, AlertMonitor
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class SentimentAnalysisAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="sentiment_analysis", agent_name="Sentiment Analysis Agent",
                          agent_type="specialized_agent", description="Social sentiment monitoring")
        CooperativeMixin.__init__(self)
        self.analyses: List[Dict] = []
        self.positive_words = ['love', 'amazing', 'great', 'wonderful', 'perfect', 'happy', 'adopted']
        self.negative_words = ['sad', 'bad', 'terrible', 'poor', 'hate', 'awful', 'waiting']
        self.register_handler('analyze_text', self._handle_analyze)
        self.register_handler('get_trends', self._handle_trends)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "analyze_sentiment":
            result = await self.analyze_sentiment(task.payload)
        elif task.task_type == "monitor_mentions":
            result = await self.monitor_mentions()
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Sentiment task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Sentiment Analysis Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Sentiment Agent completed")

    async def analyze_sentiment(self, params: Dict) -> Dict:
        text = params.get('text', '').lower()

        pos_count = sum(1 for w in self.positive_words if w in text)
        neg_count = sum(1 for w in self.negative_words if w in text)

        if pos_count > neg_count:
            sentiment = 'positive'
            score = min(1.0, 0.5 + (pos_count * 0.1))
        elif neg_count > pos_count:
            sentiment = 'negative'
            score = max(0.0, 0.5 - (neg_count * 0.1))
        else:
            sentiment = 'neutral'
            score = 0.5

        analysis = {
            'text': text[:100],
            'sentiment': sentiment,
            'score': round(score, 2),
            'analyzed_at': datetime.now().isoformat()
        }
        self.analyses.append(analysis)
        return analysis

    async def monitor_mentions(self) -> Dict:
        return {'monitored': True, 'mentions_found': 0, 'overall_sentiment': 'positive'}

    async def _handle_analyze(self, payload: Dict) -> Dict:
        return await self.analyze_sentiment(payload)
    async def _handle_trends(self, payload: Dict) -> Dict:
        recent = self.analyses[-50:]
        if not recent:
            return {'trend': 'neutral', 'sample_size': 0}
        avg = sum(a['score'] for a in recent) / len(recent)
        return {'trend': 'positive' if avg > 0.5 else 'negative', 'average_score': round(avg, 2), 'sample_size': len(recent)}
