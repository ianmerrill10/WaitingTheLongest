#!/usr/bin/env python3
"""
===============================================================================
API Monitor Agent - External API Monitoring
===============================================================================
Monitors external API health, rate limits, and performance.

Cooperates with: Debugging, AlertMonitor, Librarian
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
import aiohttp
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory, Priority


class APIMonitorAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="api_monitor", agent_name="API Monitor Agent",
                          agent_type="specialized_agent", description="External API monitoring")
        CooperativeMixin.__init__(self)
        self.apis = {
            'rescuegroups': {'url': 'https://api.rescuegroups.org/v5', 'status': 'unknown'},
            'thedogapi': {'url': 'https://api.thedogapi.com/v1', 'status': 'unknown'}
        }
        self.checks: List[Dict] = []
        self.register_handler('check_api', self._handle_check)
        self.register_handler('get_status', self._handle_status)
        self.register_handler('check_all', self._handle_check_all)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "check_apis":
            result = await self.check_all_apis()
        elif task.task_type == "check_single":
            result = await self.check_api(task.payload.get('api_name'))
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="API Monitor task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("API Monitor Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="API Monitor Agent completed")

    async def check_api(self, api_name: str) -> Dict:
        if api_name not in self.apis:
            return {'error': f'Unknown API: {api_name}'}

        api = self.apis[api_name]
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(api['url']) as response:
                    status = 'healthy' if response.status < 400 else 'degraded'
                    api['status'] = status
                    return {'api': api_name, 'status': status, 'response_code': response.status}
        except Exception as e:
            api['status'] = 'down'
            self.alert_all_agents(f'API {api_name} down', {'api': api_name, 'error': str(e)})
            return {'api': api_name, 'status': 'down', 'error': str(e)}

    async def check_all_apis(self) -> Dict:
        results = {}
        for api_name in self.apis:
            results[api_name] = await self.check_api(api_name)
        check = {'timestamp': datetime.now().isoformat(), 'results': results}
        self.checks.append(check)
        return check

    async def _handle_check(self, payload: Dict) -> Dict:
        return await self.check_api(payload.get('api_name', ''))
    async def _handle_status(self, payload: Dict) -> Dict:
        return {'apis': self.apis}
    async def _handle_check_all(self, payload: Dict) -> Dict:
        return await self.check_all_apis()
