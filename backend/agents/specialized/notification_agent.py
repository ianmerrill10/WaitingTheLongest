#!/usr/bin/env python3
"""
===============================================================================
Notification Agent - User Notification Management
===============================================================================
Manages push notifications, SMS, and in-app notifications.

Cooperates with: AlertMonitor, Email, Marketing, ALL agents
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class NotificationAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="notification", agent_name="Notification Agent",
                          agent_type="specialized_agent", description="User notification management")
        CooperativeMixin.__init__(self)
        self.notifications: List[Dict] = []
        self.register_handler('send_notification', self._handle_send)
        self.register_handler('send_push', self._handle_push)
        self.register_handler('send_sms', self._handle_sms)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "send_notification":
            result = await self.send_notification(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Notification task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Notification Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Notification Agent completed")

    async def send_notification(self, params: Dict) -> Dict:
        notification = {
            'id': f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'type': params.get('type', 'push'),
            'recipient': params.get('recipient'),
            'title': params.get('title', ''),
            'message': params.get('message', ''),
            'sent_at': datetime.now().isoformat(),
            'status': 'sent'
        }
        self.notifications.append(notification)
        return notification

    async def _handle_send(self, payload: Dict) -> Dict:
        return await self.send_notification(payload)
    async def _handle_push(self, payload: Dict) -> Dict:
        return await self.send_notification({**payload, 'type': 'push'})
    async def _handle_sms(self, payload: Dict) -> Dict:
        return await self.send_notification({**payload, 'type': 'sms'})
