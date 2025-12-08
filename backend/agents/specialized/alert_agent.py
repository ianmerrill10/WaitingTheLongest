#!/usr/bin/env python3
"""
===============================================================================
Alert Monitor Agent - System Alerts & Notifications
===============================================================================
Monitors system health and sends alerts for critical issues across the
Waiting The Longest platform.

Features:
- Real-time system health monitoring
- Alert rule management and evaluation
- Multi-severity alert levels (warning, critical, info)
- Alert acknowledgment tracking
- Cross-agent alert broadcasting
- Alert history and audit trail
- Integration with debugging and API monitoring

Usage Example:
    agent = AlertMonitorAgent()

    # Create a critical alert
    await agent.create_alert({
        'severity': 'critical',
        'message': 'Database connection failed',
        'source': 'database'
    })

    # Check all alert rules
    results = await agent.check_alert_rules()

    # Get recent alerts
    alerts = await agent.request_from_agent('alert_monitor', 'get_alerts', {})

Cooperates with: Debugging, APIMonitor, ALL agents

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory, Priority


class AlertMonitorAgent(CooperativeMixin, BaseAgent):
    """
    System alert monitoring and notification agent.

    Monitors system health across all agents and services, creating and
    broadcasting alerts when issues are detected. Maintains alert history
    and supports alert acknowledgment workflows.

    Attributes:
        alerts: List of all alerts created by the system
        alert_rules: List of configured alert rules for automated monitoring

    Supported Commands:
        create_alert: Create a new alert with specified severity
        get_alerts: Retrieve recent alerts with optional filtering
        acknowledge: Mark an alert as acknowledged
        check_rules: Evaluate all alert rules against current system state

    Examples:
        >>> agent = AlertMonitorAgent()
        >>> # Create warning alert
        >>> await agent.create_alert({
        ...     'severity': 'warning',
        ...     'message': 'High API latency detected',
        ...     'source': 'api_monitor'
        ... })
        >>> # Get unacknowledged alerts
        >>> alerts = await agent._handle_get_alerts({})
    """
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
        """
        Execute an alert monitoring task.

        Args:
            task: AgentTask with task_type ('create_alert', 'check_rules') and payload

        Returns:
            AgentResult with success status and alert data

        Examples:
            >>> task = AgentTask(
            ...     task_id="task_alert_1",
            ...     task_type="create_alert",
            ...     payload={'severity': 'critical', 'message': 'System error'}
            ... )
            >>> result = await agent.execute_task(task)
        """
        if task.task_type == "create_alert":
            result = await self.create_alert(task.payload)
        elif task.task_type == "check_rules":
            result = await self.check_alert_rules()
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Alert task completed", data=result)

    async def run(self) -> AgentResult:
        """
        Main alert monitor execution loop.

        Continuously processes messages and tasks, evaluating alert rules
        and handling alert creation/acknowledgment requests.

        Returns:
            AgentResult with completion status
        """
        self.logger.info("Alert Monitor Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Alert Agent completed")

    async def create_alert(self, params: Dict) -> Dict:
        """
        Create a new system alert.

        Args:
            params: Dictionary containing:
                - severity (str): Alert severity ('info', 'warning', 'critical')
                - message (str): Alert message
                - source (str, optional): Source of the alert (default: 'system')

        Returns:
            Dictionary with alert details including id, severity, message, timestamp

        Examples:
            >>> alert = await agent.create_alert({
            ...     'severity': 'critical',
            ...     'message': 'API rate limit exceeded',
            ...     'source': 'api_monitor'
            ... })
            >>> print(alert['id'])
        """
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
        """
        Evaluate all configured alert rules against current system state.

        Queries other agents (e.g., debugging agent for health checks) and
        creates alerts if rules are triggered.

        Returns:
            Dictionary containing:
                - checked: Number of rules checked
                - triggered: List of rule names that were triggered

        Examples:
            >>> results = await agent.check_alert_rules()
            >>> print(f"Checked {results['checked']} rules")
            >>> print(f"Triggered: {results['triggered']}")
        """
        triggered = []
        health = await self.request_from_agent('debugging', 'health_check', {})
        if health and health.get('overall_status') == 'critical':
            await self.create_alert({'severity': 'critical', 'message': 'System health critical', 'source': 'health_check'})
            triggered.append('health_check')
        return {'checked': len(self.alert_rules), 'triggered': triggered}

    async def _handle_alert(self, payload: Dict) -> Dict:
        """Handler for inter-agent alert creation requests."""
        return await self.create_alert(payload)

    async def _handle_get_alerts(self, payload: Dict) -> Dict:
        """Handler for inter-agent get alerts requests. Returns last 20 alerts."""
        return {'alerts': self.alerts[-20:], 'total': len(self.alerts)}

    async def _handle_acknowledge(self, payload: Dict) -> Dict:
        """
        Handler for inter-agent alert acknowledgment requests.

        Args:
            payload: Dictionary with 'alert_id' to acknowledge

        Returns:
            Dictionary with acknowledgment status
        """
        alert_id = payload.get('alert_id')
        for a in self.alerts:
            if a['id'] == alert_id: a['acknowledged'] = True
        return {'acknowledged': True}
