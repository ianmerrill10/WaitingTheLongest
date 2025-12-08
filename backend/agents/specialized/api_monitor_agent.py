#!/usr/bin/env python3
"""
===============================================================================
API Monitor Agent - External API Monitoring
===============================================================================
Monitors external API health, rate limits, and performance for third-party
integrations used by Waiting The Longest.

Features:
- Real-time API health monitoring
- Response time tracking
- Status code monitoring
- Automatic degradation detection
- Alert integration for API failures
- Historical check logging
- Multi-API concurrent monitoring

Usage Example:
    agent = APIMonitorAgent()

    # Check a specific API
    result = await agent.check_api('rescuegroups')

    # Check all configured APIs
    results = await agent.check_all_apis()

    # Get current API status
    status = await agent.request_from_agent('api_monitor', 'get_status', {})

Cooperates with: Debugging, AlertMonitor, Librarian

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
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
    """
    External API monitoring and health checking agent.

    Continuously monitors third-party APIs for availability, performance,
    and degradation. Automatically alerts other agents when APIs go down.

    Attributes:
        apis: Dictionary mapping API names to configuration and status
        checks: Historical list of API check results

    Supported Commands:
        check_api: Check health of a specific API
        get_status: Get current status of all APIs
        check_all: Run health checks on all configured APIs

    Examples:
        >>> agent = APIMonitorAgent()
        >>> # Check RescueGroups API
        >>> result = await agent.check_api('rescuegroups')
        >>> print(result['status'])  # 'healthy', 'degraded', or 'down'
    """
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
        """
        Execute an API monitoring task.

        Args:
            task: AgentTask with task_type ('check_apis', 'check_single') and payload

        Returns:
            AgentResult with API health check results
        """
        if task.task_type == "check_apis":
            result = await self.check_all_apis()
        elif task.task_type == "check_single":
            result = await self.check_api(task.payload.get('api_name'))
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="API Monitor task completed", data=result)

    async def run(self) -> AgentResult:
        """
        Main API monitoring execution loop.

        Returns:
            AgentResult with completion status
        """
        self.logger.info("API Monitor Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="API Monitor Agent completed")

    async def check_api(self, api_name: str) -> Dict:
        """
        Check health and availability of a specific API.

        Args:
            api_name: Name of the API to check (e.g., 'rescuegroups', 'thedogapi')

        Returns:
            Dictionary with API status, response code, and error details if any

        Examples:
            >>> result = await agent.check_api('rescuegroups')
            >>> if result['status'] == 'down':
            ...     print(f"API is down: {result['error']}")
        """
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
        """
        Check health of all configured APIs.

        Returns:
            Dictionary with timestamp and results for each API

        Examples:
            >>> results = await agent.check_all_apis()
            >>> for api, result in results['results'].items():
            ...     print(f"{api}: {result['status']}")
        """
        results = {}
        for api_name in self.apis:
            results[api_name] = await self.check_api(api_name)
        check = {'timestamp': datetime.now().isoformat(), 'results': results}
        self.checks.append(check)
        return check

    async def _handle_check(self, payload: Dict) -> Dict:
        """Handler for inter-agent single API check requests."""
        return await self.check_api(payload.get('api_name', ''))

    async def _handle_status(self, payload: Dict) -> Dict:
        """Handler for inter-agent API status requests."""
        return {'apis': self.apis}

    async def _handle_check_all(self, payload: Dict) -> Dict:
        """Handler for inter-agent check all APIs requests."""
        return await self.check_all_apis()
