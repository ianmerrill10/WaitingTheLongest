#!/usr/bin/env python3
"""
===============================================================================
Report Generator Agent - Report Creation
===============================================================================
Generates various reports from system data.

Cooperates with: Analytics, Accounting, Librarian, Marketing
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime, timedelta
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class ReportGeneratorAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="report_generator", agent_name="Report Generator Agent",
                          agent_type="specialized_agent", description="Automated report generation")
        CooperativeMixin.__init__(self)
        self.reports: List[Dict] = []
        self.register_handler('generate_report', self._handle_generate)
        self.register_handler('get_reports', self._handle_list)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "generate_report":
            result = await self.generate_report(task.payload)
        elif task.task_type == "daily_summary":
            result = await self.generate_daily_summary()
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Report task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Report Generator Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Report Agent completed")

    async def generate_report(self, params: Dict) -> Dict:
        report_type = params.get('type', 'summary')

        # Gather data from other agents
        analytics = await self.request_from_agent('analytics', 'get_dashboard', {})
        accounting = await self.request_from_agent('accounting', 'get_balance', {})

        report = {
            'id': f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'type': report_type,
            'generated_at': datetime.now().isoformat(),
            'data': {
                'analytics': analytics or {},
                'financials': accounting or {}
            }
        }
        self.reports.append(report)
        return report

    async def generate_daily_summary(self) -> Dict:
        return await self.generate_report({'type': 'daily_summary'})

    async def _handle_generate(self, payload: Dict) -> Dict:
        return await self.generate_report(payload)
    async def _handle_list(self, payload: Dict) -> Dict:
        return {'reports': self.reports[-10:], 'total': len(self.reports)}
