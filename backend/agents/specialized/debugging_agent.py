#!/usr/bin/env python3
"""
===============================================================================
Debugging Agent - System Diagnostics & Error Resolution
===============================================================================
Monitors system health, identifies issues, and helps resolve errors.

Features:
- Error log analysis
- Performance monitoring
- Database health checks
- API endpoint testing
- Memory/resource monitoring
- Automated error resolution
- Crash dump analysis
- Issue tracking

Cooperates with: ALL agents (system health monitor), APIMonitor, AlertMonitor
===============================================================================
"""

import os
import sys
import asyncio
import psutil
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority
from agents.protocols import CooperativeMixin, DataCategory, Priority


@dataclass
class ErrorReport:
    """Error report structure"""
    error_id: str
    error_type: str
    message: str
    stack_trace: str
    source: str
    severity: str  # low, medium, high, critical
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class HealthCheck:
    """System health check result"""
    component: str
    status: str  # healthy, warning, critical
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class DebuggingAgent(CooperativeMixin, BaseAgent):
    """
    System diagnostics and debugging agent.

    Commands:
    - health_check: Run full system health check
    - analyze_logs: Analyze error logs
    - test_endpoints: Test API endpoints
    - check_database: Check database health
    - monitor_resources: Monitor system resources
    - diagnose_error: Diagnose a specific error
    - get_error_report: Get error report
    - clear_cache: Clear system caches
    - restart_service: Restart a service
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="debugging",
            agent_name="Debugging Agent",
            agent_type="specialized_agent",
            description="System diagnostics and error resolution"
        )
        CooperativeMixin.__init__(self)

        self.error_log: List[ErrorReport] = []
        self.health_history: List[HealthCheck] = []
        self.known_issues: Dict[str, Dict] = {}

        # Register handlers
        self.register_handler('health_check', self._handle_health_check)
        self.register_handler('diagnose_error', self._handle_diagnose)
        self.register_handler('report_error', self._handle_error_report)
        self.register_handler('get_status', self._handle_status)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a debugging task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "health_check":
                result = await self.run_health_check()
            elif task.task_type == "analyze_logs":
                result = await self.analyze_logs(task.payload)
            elif task.task_type == "test_endpoints":
                result = await self.test_endpoints()
            elif task.task_type == "check_database":
                result = await self.check_database()
            elif task.task_type == "monitor_resources":
                result = await self.monitor_resources()
            elif task.task_type == "diagnose_error":
                result = await self.diagnose_error(task.payload)
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Debugging task completed: {task.task_type}",
                data=result,
                duration_seconds=(task.completed_at - task.started_at).total_seconds()
            )

        except Exception as e:
            self.logger.error(f"Debugging task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main debugging agent loop"""
        self.logger.info("Debugging Agent starting")
        processed = 0

        # Run initial health check
        await self.run_health_check()

        while self.status.value == "running":
            await self.process_messages()

            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Debugging Agent completed", items_processed=processed)

    async def run_health_check(self) -> Dict:
        """Run comprehensive system health check"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }

        # Check database
        db_health = await self.check_database()
        results['components']['database'] = db_health

        # Check resources
        resource_health = await self.monitor_resources()
        results['components']['resources'] = resource_health

        # Check API
        api_health = await self.test_endpoints()
        results['components']['api'] = api_health

        # Determine overall status
        statuses = [c.get('status', 'unknown') for c in results['components'].values()]
        if 'critical' in statuses:
            results['overall_status'] = 'critical'
            self.alert_all_agents('System Critical', {'health': results})
        elif 'warning' in statuses:
            results['overall_status'] = 'warning'

        # Share health data
        self.share_discovery(
            DataCategory.ANALYTICS,
            'System Health Check',
            results,
            tags=['health', 'monitoring']
        )

        return results

    async def check_database(self) -> Dict:
        """Check database health"""
        try:
            db = self.get_db()
            from app.models import Animal, Shelter

            # Test basic queries
            animal_count = db.query(Animal).count()
            shelter_count = db.query(Shelter).count()

            db.close()

            return {
                'status': 'healthy',
                'animal_count': animal_count,
                'shelter_count': shelter_count,
                'connection': 'ok'
            }

        except Exception as e:
            self.logger.error(f"Database check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'connection': 'failed'
            }

    async def monitor_resources(self) -> Dict:
        """Monitor system resources"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            status = 'healthy'
            warnings = []

            if cpu_percent > 90:
                status = 'warning'
                warnings.append('High CPU usage')
            if memory.percent > 90:
                status = 'warning'
                warnings.append('High memory usage')
            if disk.percent > 90:
                status = 'warning'
                warnings.append('Low disk space')

            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'warnings': warnings
            }

        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }

    async def test_endpoints(self) -> Dict:
        """Test API endpoints"""
        import aiohttp

        endpoints = [
            ('health', 'http://localhost:8000/health'),
            ('animals', 'http://localhost:8000/api/v1/animals?limit=1'),
            ('shelters', 'http://localhost:8000/api/v1/shelters?limit=1'),
        ]

        results = {}
        overall_status = 'healthy'

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            for name, url in endpoints:
                try:
                    async with session.get(url) as response:
                        results[name] = {
                            'status': 'healthy' if response.status == 200 else 'warning',
                            'status_code': response.status,
                            'response_time_ms': 0  # Would need timing
                        }
                        if response.status != 200:
                            overall_status = 'warning'
                except Exception as e:
                    results[name] = {
                        'status': 'critical',
                        'error': str(e)
                    }
                    overall_status = 'critical'

        return {
            'status': overall_status,
            'endpoints': results
        }

    async def analyze_logs(self, params: Dict) -> Dict:
        """Analyze error logs"""
        log_dir = Path(__file__).parent.parent / "logs"
        time_window = params.get('hours', 24)
        cutoff = datetime.now() - timedelta(hours=time_window)

        errors_found = []
        warnings_found = []

        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if 'ERROR' in line:
                                errors_found.append({
                                    'file': log_file.name,
                                    'line': line.strip()[:200]
                                })
                            elif 'WARNING' in line:
                                warnings_found.append({
                                    'file': log_file.name,
                                    'line': line.strip()[:200]
                                })
                except Exception as e:
                    self.logger.warning(f"Could not read log file {log_file}: {e}")

        return {
            'time_window_hours': time_window,
            'errors_count': len(errors_found),
            'warnings_count': len(warnings_found),
            'recent_errors': errors_found[-10:],
            'recent_warnings': warnings_found[-10:]
        }

    async def diagnose_error(self, params: Dict) -> Dict:
        """Diagnose a specific error"""
        error_message = params.get('error', '')
        error_type = params.get('type', 'unknown')

        diagnosis = {
            'error': error_message,
            'type': error_type,
            'possible_causes': [],
            'suggested_fixes': [],
            'severity': 'medium'
        }

        # Common error patterns
        if 'connection' in error_message.lower():
            diagnosis['possible_causes'].append('Database or network connection issue')
            diagnosis['suggested_fixes'].append('Check database service is running')
            diagnosis['suggested_fixes'].append('Verify network connectivity')

        if 'timeout' in error_message.lower():
            diagnosis['possible_causes'].append('Operation took too long')
            diagnosis['suggested_fixes'].append('Increase timeout values')
            diagnosis['suggested_fixes'].append('Check for slow queries')

        if 'memory' in error_message.lower():
            diagnosis['possible_causes'].append('Insufficient memory')
            diagnosis['suggested_fixes'].append('Restart application to free memory')
            diagnosis['suggested_fixes'].append('Increase system memory')
            diagnosis['severity'] = 'high'

        if 'permission' in error_message.lower() or 'access' in error_message.lower():
            diagnosis['possible_causes'].append('Permission or access issue')
            diagnosis['suggested_fixes'].append('Check file/folder permissions')
            diagnosis['suggested_fixes'].append('Verify user credentials')

        return diagnosis

    def report_error(self, error_type: str, message: str, stack_trace: str = "", source: str = "unknown"):
        """Report an error to the debugging agent"""
        report = ErrorReport(
            error_id=f"err_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            source=source,
            severity=self._determine_severity(error_type, message)
        )

        self.error_log.append(report)

        if report.severity == 'critical':
            self.alert_all_agents('Critical Error', {
                'error_id': report.error_id,
                'message': message,
                'source': source
            })

        return report.error_id

    def _determine_severity(self, error_type: str, message: str) -> str:
        """Determine error severity"""
        critical_keywords = ['fatal', 'crash', 'corruption', 'data loss']
        high_keywords = ['memory', 'timeout', 'connection refused']
        medium_keywords = ['warning', 'deprecated', 'slow']

        message_lower = message.lower()

        if any(kw in message_lower for kw in critical_keywords):
            return 'critical'
        if any(kw in message_lower for kw in high_keywords):
            return 'high'
        if any(kw in message_lower for kw in medium_keywords):
            return 'medium'
        return 'low'

    async def _handle_health_check(self, payload: Dict) -> Dict:
        return await self.run_health_check()

    async def _handle_diagnose(self, payload: Dict) -> Dict:
        return await self.diagnose_error(payload)

    async def _handle_error_report(self, payload: Dict) -> Dict:
        error_id = self.report_error(
            payload.get('type', 'unknown'),
            payload.get('message', ''),
            payload.get('stack_trace', ''),
            payload.get('source', 'unknown')
        )
        return {'error_id': error_id, 'logged': True}

    async def _handle_status(self, payload: Dict) -> Dict:
        return {
            'agent': 'debugging',
            'errors_logged': len(self.error_log),
            'recent_errors': len([e for e in self.error_log if (datetime.now() - e.timestamp).hours < 1]),
            'health_checks': len(self.health_history)
        }


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Debugging Agent CLI")
    parser.add_argument('--health', action='store_true', help='Run health check')
    parser.add_argument('--logs', action='store_true', help='Analyze logs')
    parser.add_argument('--resources', action='store_true', help='Check resources')
    parser.add_argument('--diagnose', type=str, help='Diagnose error message')

    args = parser.parse_args()
    agent = DebuggingAgent()

    if args.health:
        result = asyncio.run(agent.run_health_check())
        print(json.dumps(result, indent=2))
    elif args.logs:
        result = asyncio.run(agent.analyze_logs({'hours': 24}))
        print(json.dumps(result, indent=2))
    elif args.resources:
        result = asyncio.run(agent.monitor_resources())
        print(json.dumps(result, indent=2))
    elif args.diagnose:
        result = asyncio.run(agent.diagnose_error({'error': args.diagnose}))
        print(json.dumps(result, indent=2))
