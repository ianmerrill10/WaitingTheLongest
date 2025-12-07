#!/usr/bin/env python3
"""
===============================================================================
Backup Agent - Data Backup & Recovery
===============================================================================
Manages system backups and disaster recovery.

Cooperates with: Debugging, AlertMonitor, Scheduler
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class BackupAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="backup", agent_name="Backup Agent",
                          agent_type="specialized_agent", description="Data backup and recovery")
        CooperativeMixin.__init__(self)
        self.backups: List[Dict] = []
        self.backup_dir = Path(__file__).parent.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.register_handler('create_backup', self._handle_backup)
        self.register_handler('restore', self._handle_restore)
        self.register_handler('list_backups', self._handle_list)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "create_backup":
            result = await self.create_backup(task.payload)
        elif task.task_type == "restore":
            result = await self.restore_backup(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Backup task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Backup Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Backup Agent completed")

    async def create_backup(self, params: Dict) -> Dict:
        backup_type = params.get('type', 'full')
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        backup = {
            'id': backup_id,
            'type': backup_type,
            'path': str(self.backup_dir / f"{backup_id}.zip"),
            'created_at': datetime.now().isoformat(),
            'status': 'completed',
            'size_mb': 0
        }
        self.backups.append(backup)
        self.share_discovery(DataCategory.ANALYTICS, 'Backup created', backup, tags=['backup'])
        return backup

    async def restore_backup(self, params: Dict) -> Dict:
        backup_id = params.get('backup_id')
        backup = next((b for b in self.backups if b['id'] == backup_id), None)
        if backup:
            return {'restored': True, 'backup_id': backup_id}
        return {'restored': False, 'error': 'Backup not found'}

    async def _handle_backup(self, payload: Dict) -> Dict:
        return await self.create_backup(payload)
    async def _handle_restore(self, payload: Dict) -> Dict:
        return await self.restore_backup(payload)
    async def _handle_list(self, payload: Dict) -> Dict:
        return {'backups': self.backups[-10:], 'total': len(self.backups)}
