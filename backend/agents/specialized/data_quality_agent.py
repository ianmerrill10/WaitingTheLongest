#!/usr/bin/env python3
"""
===============================================================================
Data Quality Agent - Data Validation & Cleanup
===============================================================================
Ensures data quality across the system through validation, deduplication,
and automated cleanup processes.

Features:
- Data validation and verification
- Duplicate detection and merging
- Missing data identification
- Data normalization
- Quality scoring
- Automated cleanup
- Data consistency checks
- Orphan record handling

Usage Example:
    agent = DataQualityAgent()

    # Run comprehensive audit
    audit = await agent.run_audit({'entity_type': 'all'})
    print(f"Overall quality score: {audit['overall_quality_score']}")

    # Find duplicate shelters
    dupes = await agent.find_duplicates({'entity_type': 'shelters'})

    # Cleanup orphan records (dry run)
    cleanup = await agent.cleanup({'type': 'orphans', 'dry_run': True})

Cooperates with: Librarian, IntakeSpecialist, Debugging, AlertMonitor

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority
from agents.protocols import CooperativeMixin, DataCategory, Priority


@dataclass
class QualityReport:
    """
    Data quality audit report.

    Attributes:
        report_id: Unique identifier for the report
        entity_type: Type of entity audited (animals, shelters, etc.)
        total_records: Total number of records checked
        issues_found: Number of records with issues
        issues_fixed: Number of issues automatically fixed
        quality_score: Overall quality score (0-100)
        details: List of specific issues found
        created_at: Timestamp when report was created
    """
    report_id: str
    entity_type: str
    total_records: int
    issues_found: int
    issues_fixed: int
    quality_score: float
    details: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class DataQualityAgent(CooperativeMixin, BaseAgent):
    """
    Data quality management agent.

    Commands:
    - run_audit: Run full data quality audit
    - find_duplicates: Find duplicate records
    - validate_entity: Validate specific entity
    - cleanup: Run cleanup operations
    - normalize_data: Normalize data formats
    - fix_issues: Auto-fix quality issues
    - get_quality_score: Get data quality score
    - find_missing: Find records with missing data
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="data_quality",
            agent_name="Data Quality Agent",
            agent_type="specialized_agent",
            description="Data validation and quality management"
        )
        CooperativeMixin.__init__(self)

        self.quality_reports: List[QualityReport] = []
        self.known_issues: Dict[str, List[Dict]] = {}

        # Register handlers
        self.register_handler('run_audit', self._handle_audit)
        self.register_handler('find_duplicates', self._handle_duplicates)
        self.register_handler('cleanup', self._handle_cleanup)
        self.register_handler('get_quality_score', self._handle_quality_score)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a data quality task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "run_audit":
                result = await self.run_audit(task.payload)
            elif task.task_type == "find_duplicates":
                result = await self.find_duplicates(task.payload)
            elif task.task_type == "cleanup":
                result = await self.cleanup(task.payload)
            elif task.task_type == "normalize":
                result = await self.normalize_data(task.payload)
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Data quality task completed: {task.task_type}",
                data=result
            )

        except Exception as e:
            self.logger.error(f"Data quality task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main data quality agent loop"""
        self.logger.info("Data Quality Agent starting")
        processed = 0

        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Data Quality Agent completed", items_processed=processed)

    async def run_audit(self, params: Dict) -> Dict:
        """Run comprehensive data quality audit"""
        entity_type = params.get('entity_type', 'all')

        results = {
            'audit_id': f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'entities': {}
        }

        if entity_type in ['all', 'animals']:
            results['entities']['animals'] = await self._audit_animals()

        if entity_type in ['all', 'shelters']:
            results['entities']['shelters'] = await self._audit_shelters()

        # Calculate overall score
        scores = [e['quality_score'] for e in results['entities'].values()]
        results['overall_quality_score'] = sum(scores) / len(scores) if scores else 0

        # Share results
        self.share_discovery(
            DataCategory.ANALYTICS,
            'Data Quality Audit Results',
            results,
            tags=['audit', 'quality', 'report']
        )

        return results

    async def _audit_animals(self) -> Dict:
        """Audit animal records"""
        try:
            db = self.get_db()
            from app.models import Animal

            animals = db.query(Animal).all()
            total = len(animals)
            issues = []

            for animal in animals:
                animal_issues = []

                # Check for missing name
                if not animal.name or animal.name.strip() == '':
                    animal_issues.append({'field': 'name', 'issue': 'missing'})

                # Check for missing photos
                if not animal.photo_url:
                    animal_issues.append({'field': 'photo_url', 'issue': 'missing'})

                # Check for missing intake date
                if not animal.intake_date:
                    animal_issues.append({'field': 'intake_date', 'issue': 'missing'})

                # Check for invalid status
                if animal.status not in ['available', 'adopted', 'pending', 'hold']:
                    animal_issues.append({'field': 'status', 'issue': 'invalid', 'value': animal.status})

                # Check for very old intake dates without update
                if animal.intake_date:
                    days = (datetime.now().date() - animal.intake_date).days
                    if days > 730:  # 2 years
                        animal_issues.append({'field': 'intake_date', 'issue': 'stale', 'days': days})

                if animal_issues:
                    issues.append({
                        'animal_id': animal.id,
                        'name': animal.name,
                        'issues': animal_issues
                    })

            db.close()

            quality_score = ((total - len(issues)) / total * 100) if total > 0 else 100

            return {
                'total_records': total,
                'records_with_issues': len(issues),
                'quality_score': round(quality_score, 2),
                'issues': issues[:50]  # Limit to first 50
            }

        except Exception as e:
            self.logger.error(f"Animal audit failed: {e}")
            return {'error': str(e)}

    async def _audit_shelters(self) -> Dict:
        """Audit shelter records"""
        try:
            db = self.get_db()
            from app.models import Shelter

            shelters = db.query(Shelter).all()
            total = len(shelters)
            issues = []

            for shelter in shelters:
                shelter_issues = []

                if not shelter.name:
                    shelter_issues.append({'field': 'name', 'issue': 'missing'})

                if not shelter.state:
                    shelter_issues.append({'field': 'state', 'issue': 'missing'})

                if not shelter.city:
                    shelter_issues.append({'field': 'city', 'issue': 'missing'})

                # Check for valid email format
                if shelter.email and '@' not in shelter.email:
                    shelter_issues.append({'field': 'email', 'issue': 'invalid_format'})

                if shelter_issues:
                    issues.append({
                        'shelter_id': shelter.id,
                        'name': shelter.name,
                        'issues': shelter_issues
                    })

            db.close()

            quality_score = ((total - len(issues)) / total * 100) if total > 0 else 100

            return {
                'total_records': total,
                'records_with_issues': len(issues),
                'quality_score': round(quality_score, 2),
                'issues': issues[:50]
            }

        except Exception as e:
            self.logger.error(f"Shelter audit failed: {e}")
            return {'error': str(e)}

    async def find_duplicates(self, params: Dict) -> Dict:
        """Find duplicate records"""
        entity_type = params.get('entity_type', 'shelters')
        duplicates = []

        try:
            db = self.get_db()

            if entity_type == 'shelters':
                from app.models import Shelter
                from sqlalchemy import func

                # Find shelters with same name and state
                dupes = db.query(
                    Shelter.name, Shelter.state, func.count(Shelter.id).label('count')
                ).group_by(Shelter.name, Shelter.state).having(func.count(Shelter.id) > 1).all()

                for name, state, count in dupes:
                    matching = db.query(Shelter).filter(
                        Shelter.name == name, Shelter.state == state
                    ).all()
                    duplicates.append({
                        'name': name,
                        'state': state,
                        'count': count,
                        'ids': [s.id for s in matching]
                    })

            db.close()

        except Exception as e:
            self.logger.error(f"Duplicate detection failed: {e}")
            return {'error': str(e)}

        return {'entity_type': entity_type, 'duplicates': duplicates, 'count': len(duplicates)}

    async def cleanup(self, params: Dict) -> Dict:
        """Run cleanup operations"""
        cleanup_type = params.get('type', 'orphans')
        dry_run = params.get('dry_run', True)
        cleaned = 0

        try:
            db = self.get_db()

            if cleanup_type == 'orphans':
                # Find animals with invalid shelter_id
                from app.models import Animal, Shelter
                orphans = db.query(Animal).filter(
                    ~Animal.shelter_id.in_(db.query(Shelter.id))
                ).all()

                if not dry_run:
                    for animal in orphans:
                        db.delete(animal)
                    db.commit()
                    cleaned = len(orphans)
                else:
                    cleaned = len(orphans)

            elif cleanup_type == 'stale':
                # Mark very old available animals for review
                from app.models import Animal
                stale_date = datetime.now().date() - timedelta(days=730)
                stale = db.query(Animal).filter(
                    Animal.intake_date < stale_date,
                    Animal.status == 'available'
                ).all()
                cleaned = len(stale)

            db.close()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return {'error': str(e)}

        return {
            'cleanup_type': cleanup_type,
            'dry_run': dry_run,
            'affected_records': cleaned
        }

    async def normalize_data(self, params: Dict) -> Dict:
        """Normalize data formats"""
        field = params.get('field')
        normalized = 0

        # State abbreviation normalization
        state_map = {
            'california': 'CA', 'new york': 'NY', 'texas': 'TX',
            'florida': 'FL', 'pennsylvania': 'PA', 'illinois': 'IL'
        }

        try:
            db = self.get_db()

            if field == 'state':
                from app.models import Shelter
                shelters = db.query(Shelter).all()

                for shelter in shelters:
                    if shelter.state and len(shelter.state) > 2:
                        normalized_state = state_map.get(shelter.state.lower())
                        if normalized_state:
                            shelter.state = normalized_state
                            normalized += 1

                db.commit()

            db.close()

        except Exception as e:
            self.logger.error(f"Normalization failed: {e}")
            return {'error': str(e)}

        return {'field': field, 'normalized_count': normalized}

    async def _handle_audit(self, payload: Dict) -> Dict:
        """Handler for inter-agent audit requests."""
        return await self.run_audit(payload)

    async def _handle_duplicates(self, payload: Dict) -> Dict:
        """Handler for inter-agent duplicate detection requests."""
        return await self.find_duplicates(payload)

    async def _handle_cleanup(self, payload: Dict) -> Dict:
        """Handler for inter-agent cleanup requests."""
        return await self.cleanup(payload)

    async def _handle_quality_score(self, payload: Dict) -> Dict:
        """Handler for inter-agent quality score requests."""
        audit = await self.run_audit({'entity_type': 'all'})
        return {'quality_score': audit.get('overall_quality_score', 0)}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Data Quality Agent CLI")
    parser.add_argument('--audit', type=str, choices=['all', 'animals', 'shelters'], help='Run audit')
    parser.add_argument('--duplicates', type=str, choices=['shelters', 'animals'], help='Find duplicates')
    parser.add_argument('--cleanup', type=str, help='Run cleanup')

    args = parser.parse_args()
    agent = DataQualityAgent()

    if args.audit:
        result = asyncio.run(agent.run_audit({'entity_type': args.audit}))
        print(json.dumps(result, indent=2, default=str))
    elif args.duplicates:
        result = asyncio.run(agent.find_duplicates({'entity_type': args.duplicates}))
        print(json.dumps(result, indent=2))
    elif args.cleanup:
        result = asyncio.run(agent.cleanup({'type': args.cleanup, 'dry_run': True}))
        print(json.dumps(result, indent=2))
