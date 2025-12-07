#!/usr/bin/env python3
"""
===============================================================================
Adoption Matcher Agent - Pet-Adopter Matching
===============================================================================
Matches potential adopters with suitable pets based on preferences.

Cooperates with: Librarian, Notification, Analytics
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class AdoptionMatcherAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="adoption_matcher", agent_name="Adoption Matcher Agent",
                          agent_type="specialized_agent", description="Pet-adopter matching system")
        CooperativeMixin.__init__(self)
        self.matches: List[Dict] = []
        self.register_handler('find_matches', self._handle_matches)
        self.register_handler('score_match', self._handle_score)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "find_matches":
            result = await self.find_matches(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Matcher task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Adoption Matcher Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Matcher Agent completed")

    async def find_matches(self, params: Dict) -> Dict:
        preferences = params.get('preferences', {})
        limit = params.get('limit', 10)

        # Get available animals from Librarian
        animals = await self.request_from_agent('librarian', 'search', {
            'category': 'animal', 'query': preferences.get('type', 'dog')
        })

        matches = []
        if animals and animals.get('results'):
            for animal in animals['results'][:limit]:
                score = self._calculate_match_score(animal, preferences)
                matches.append({'animal': animal, 'score': score})

        matches.sort(key=lambda x: x['score'], reverse=True)
        return {'matches': matches[:limit], 'count': len(matches)}

    def _calculate_match_score(self, animal: Dict, preferences: Dict) -> float:
        score = 50.0
        if preferences.get('size') and animal.get('size') == preferences['size']:
            score += 20
        if preferences.get('age') and preferences['age'] in str(animal.get('age', '')):
            score += 15
        score += min(animal.get('days_waiting', 0) / 10, 15)  # Bonus for long-waiting
        return min(score, 100)

    async def _handle_matches(self, payload: Dict) -> Dict:
        return await self.find_matches(payload)
    async def _handle_score(self, payload: Dict) -> Dict:
        return {'score': self._calculate_match_score(payload.get('animal', {}), payload.get('preferences', {}))}
