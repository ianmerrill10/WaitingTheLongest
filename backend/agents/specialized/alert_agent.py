#!/usr/bin/env python3
"""
===============================================================================
Alert Monitor Agent - System Alerts & Notifications
===============================================================================
Monitors system health and sends alerts for critical issues.

Cooperates with: Debugging, APIMonitor, ALL agents
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory, Priority


class AlertMonitorAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="alert_monitor", agent_name="Alert Monitor Agent",
                          agent_type="specialized_agent", description="System alerts and monitoring")
        CooperativeMixin.__init__(self)
        self.alerts: List[Dict] = []
        self.alert_rules: List[Dict] = []
        self.register_handler('create_alert', self._handle_alert)
        self.register_handler('get_alerts', self._handle_get_alerts)
        self.register_handler('acknowledge', self._handle_acknowledge)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "create_alert":
            result = await self.create_alert(task.payload)
        elif task.task_type == "check_rules":
            result = await self.check_alert_rules()
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Alert task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Alert Monitor Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Alert Agent completed")

    async def create_alert(self, params: Dict) -> Dict:
        alert = {
            'id': f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'severity': params.get('severity', 'warning'),
            'message': params.get('message', ''),
            'source': params.get('source', 'system'),
            'created_at': datetime.now().isoformat(),
            'acknowledged': False
        }
        self.alerts.append(alert)
        if alert['severity'] == 'critical':
            self.alert_all_agents('Critical Alert', alert)
        return alert

    async def check_alert_rules(self) -> Dict:
        triggered = []
        health = await self.request_from_agent('debugging', 'health_check', {})
        if health and health.get('overall_status') == 'critical':
            await self.create_alert({'severity': 'critical', 'message': 'System health critical', 'source': 'health_check'})
            triggered.append('health_check')
        return {'checked': len(self.alert_rules), 'triggered': triggered}

    async def _handle_alert(self, payload: Dict) -> Dict:
        return await self.create_alert(payload)
    async def _handle_get_alerts(self, payload: Dict) -> Dict:
        return {'alerts': self.alerts[-20:], 'total': len(self.alerts)}
    async def _handle_acknowledge(self, payload: Dict) -> Dict:
        alert_id = payload.get('alert_id')
        for a in self.alerts:
            if a['id'] == alert_id: a['acknowledged'] = True
        return {'acknowledged': True}
