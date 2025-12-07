#!/usr/bin/env python3
"""
===============================================================================
Accounting Agent - Financial Tracking & Reporting
===============================================================================
Manages financial data, donations, expenses, and generates financial reports.

Features:
- Donation tracking and reconciliation
- Expense categorization
- Budget monitoring
- Financial reporting
- Tax document preparation
- Amazon Associates revenue tracking
- Fundraiser accounting

Cooperates with: DonationTracker, ReportGenerator, AlertMonitor
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority
from agents.protocols import CooperativeMixin, DataCategory, Priority


@dataclass
class Transaction:
    """Financial transaction"""
    transaction_id: str
    type: str  # donation, expense, revenue
    amount: Decimal
    category: str
    description: str
    date: datetime = field(default_factory=datetime.now)
    source: str = ""
    verified: bool = False


class AccountingAgent(CooperativeMixin, BaseAgent):
    """
    Financial tracking and reporting agent.

    Commands:
    - record_donation: Record a donation
    - record_expense: Record an expense
    - get_balance: Get current balance
    - generate_report: Generate financial report
    - get_donations: Get donation summary
    - get_expenses: Get expense breakdown
    - reconcile: Reconcile accounts
    - track_amazon: Track Amazon Associates revenue
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="accounting",
            agent_name="Accounting Agent",
            agent_type="specialized_agent",
            description="Financial tracking and reporting"
        )
        CooperativeMixin.__init__(self)

        self.transactions: List[Transaction] = []
        self.budgets: Dict[str, Decimal] = {}

        # Register handlers
        self.register_handler('record_donation', self._handle_donation)
        self.register_handler('record_expense', self._handle_expense)
        self.register_handler('get_summary', self._handle_summary)
        self.register_handler('get_balance', self._handle_balance)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute an accounting task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "record_donation":
                result = await self.record_donation(task.payload)
            elif task.task_type == "record_expense":
                result = await self.record_expense(task.payload)
            elif task.task_type == "generate_report":
                result = await self.generate_report(task.payload)
            elif task.task_type == "get_balance":
                result = await self.get_balance()
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Accounting task completed: {task.task_type}",
                data=result
            )

        except Exception as e:
            self.logger.error(f"Accounting task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main accounting agent loop"""
        self.logger.info("Accounting Agent starting")
        processed = 0

        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Accounting Agent completed", items_processed=processed)

    async def record_donation(self, data: Dict) -> Dict:
        """Record a donation"""
        transaction = Transaction(
            transaction_id=f"don_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type='donation',
            amount=Decimal(str(data.get('amount', 0))),
            category=data.get('category', 'general'),
            description=data.get('description', ''),
            source=data.get('source', 'direct')
        )
        self.transactions.append(transaction)
        self.logger.info(f"Recorded donation: ${transaction.amount}")
        return {'transaction_id': transaction.transaction_id, 'amount': float(transaction.amount)}

    async def record_expense(self, data: Dict) -> Dict:
        """Record an expense"""
        transaction = Transaction(
            transaction_id=f"exp_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type='expense',
            amount=Decimal(str(data.get('amount', 0))),
            category=data.get('category', 'operations'),
            description=data.get('description', '')
        )
        self.transactions.append(transaction)
        return {'transaction_id': transaction.transaction_id, 'amount': float(transaction.amount)}

    async def get_balance(self) -> Dict:
        """Calculate current balance"""
        donations = sum(t.amount for t in self.transactions if t.type == 'donation')
        expenses = sum(t.amount for t in self.transactions if t.type == 'expense')
        revenue = sum(t.amount for t in self.transactions if t.type == 'revenue')
        return {
            'total_donations': float(donations),
            'total_expenses': float(expenses),
            'total_revenue': float(revenue),
            'balance': float(donations + revenue - expenses)
        }

    async def generate_report(self, params: Dict) -> Dict:
        """Generate financial report"""
        period = params.get('period', 'month')
        now = datetime.now()

        if period == 'month':
            start_date = now.replace(day=1)
        elif period == 'year':
            start_date = now.replace(month=1, day=1)
        else:
            start_date = now - timedelta(days=30)

        period_transactions = [t for t in self.transactions if t.date >= start_date]

        by_category = {}
        for t in period_transactions:
            if t.category not in by_category:
                by_category[t.category] = {'donations': Decimal(0), 'expenses': Decimal(0)}
            if t.type == 'donation':
                by_category[t.category]['donations'] += t.amount
            elif t.type == 'expense':
                by_category[t.category]['expenses'] += t.amount

        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'transaction_count': len(period_transactions),
            'by_category': {k: {'donations': float(v['donations']), 'expenses': float(v['expenses'])} for k, v in by_category.items()},
            'balance': float(sum(t.amount if t.type in ['donation', 'revenue'] else -t.amount for t in period_transactions))
        }

    async def _handle_donation(self, payload: Dict) -> Dict:
        return await self.record_donation(payload)

    async def _handle_expense(self, payload: Dict) -> Dict:
        return await self.record_expense(payload)

    async def _handle_summary(self, payload: Dict) -> Dict:
        return await self.generate_report(payload)

    async def _handle_balance(self, payload: Dict) -> Dict:
        return await self.get_balance()


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Accounting Agent CLI")
    parser.add_argument('--balance', action='store_true', help='Get balance')
    parser.add_argument('--report', type=str, choices=['month', 'year'], help='Generate report')

    args = parser.parse_args()
    agent = AccountingAgent()

    if args.balance:
        result = asyncio.run(agent.get_balance())
        print(json.dumps(result, indent=2))
    elif args.report:
        result = asyncio.run(agent.generate_report({'period': args.report}))
        print(json.dumps(result, indent=2))
