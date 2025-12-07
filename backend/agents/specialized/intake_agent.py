#!/usr/bin/env python3
"""
===============================================================================
Intake Specialist Agent - New Animal Processing
===============================================================================
Handles the intake of new animals into the system, validates data,
enriches profiles, and ensures quality standards.

Features:
- New animal data validation
- Profile enrichment
- Photo processing coordination
- Breed identification assistance
- Age estimation
- Health status tracking
- Shelter coordination
- Duplicate detection

Cooperates with: DataQuality, ImageProcessing, Librarian, Notification
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority
from agents.protocols import CooperativeMixin, DataCategory, Priority


@dataclass
class IntakeRecord:
    """Animal intake record"""
    intake_id: str
    animal_data: Dict[str, Any]
    source: str
    status: str = "pending"  # pending, validated, enriched, complete, rejected
    validation_errors: List[str] = field(default_factory=list)
    enrichments: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class IntakeSpecialistAgent(CooperativeMixin, BaseAgent):
    """
    New animal intake processing agent.

    Commands:
    - process_intake: Process a new animal intake
    - validate_data: Validate animal data
    - enrich_profile: Enrich animal profile
    - detect_duplicates: Check for duplicate entries
    - estimate_age: Estimate animal age from description
    - identify_breed: Help identify breed
    - batch_intake: Process multiple intakes
    - get_pending: Get pending intakes
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="intake_specialist",
            agent_name="Intake Specialist Agent",
            agent_type="specialized_agent",
            description="New animal intake processing"
        )
        CooperativeMixin.__init__(self)

        self.intake_queue: List[IntakeRecord] = []
        self.processed: List[IntakeRecord] = []

        # Register handlers
        self.register_handler('process_intake', self._handle_intake)
        self.register_handler('validate', self._handle_validate)
        self.register_handler('enrich', self._handle_enrich)
        self.register_handler('get_pending', self._handle_pending)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute an intake task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "process_intake":
                result = await self.process_intake(task.payload)
            elif task.task_type == "batch_intake":
                result = await self.batch_intake(task.payload.get('animals', []))
            elif task.task_type == "validate_data":
                result = await self.validate_data(task.payload)
            elif task.task_type == "detect_duplicates":
                result = await self.detect_duplicates(task.payload)
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Intake task completed: {task.task_type}",
                data=result
            )

        except Exception as e:
            self.logger.error(f"Intake task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main intake agent loop"""
        self.logger.info("Intake Specialist Agent starting")
        processed = 0

        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Intake Agent completed", items_processed=processed)

    async def process_intake(self, animal_data: Dict) -> Dict:
        """Process a new animal intake"""
        intake = IntakeRecord(
            intake_id=f"intake_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            animal_data=animal_data,
            source=animal_data.get('source', 'manual')
        )

        # Step 1: Validate data
        validation = await self.validate_data(animal_data)
        if validation['errors']:
            intake.status = 'rejected'
            intake.validation_errors = validation['errors']
            return {'intake_id': intake.intake_id, 'status': 'rejected', 'errors': validation['errors']}

        intake.status = 'validated'

        # Step 2: Check for duplicates
        duplicates = await self.detect_duplicates(animal_data)
        if duplicates.get('duplicates'):
            intake.enrichments['possible_duplicates'] = duplicates['duplicates']

        # Step 3: Enrich profile
        enriched = await self.enrich_profile(animal_data)
        intake.enrichments.update(enriched)
        intake.status = 'enriched'

        # Step 4: Request image processing if photo available
        if animal_data.get('photo_url'):
            await self.request_from_agent(
                'image_processing',
                'process_animal_photo',
                {'photo_url': animal_data['photo_url'], 'animal_id': intake.intake_id}
            )

        # Step 5: Save to database
        saved = await self._save_animal(intake)

        if saved:
            intake.status = 'complete'
            self.processed.append(intake)

            # Notify relevant agents
            self.share_discovery(
                DataCategory.ANIMAL,
                f"New animal intake: {animal_data.get('name', 'Unknown')}",
                {'intake_id': intake.intake_id, 'animal': animal_data},
                tags=['new', 'intake', animal_data.get('animal_type', 'unknown')]
            )

        return {
            'intake_id': intake.intake_id,
            'status': intake.status,
            'enrichments': intake.enrichments
        }

    async def validate_data(self, data: Dict) -> Dict:
        """Validate animal data"""
        errors = []
        warnings = []

        # Required fields
        required = ['name', 'animal_type']
        for field in required:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate animal type
        valid_types = ['dog', 'cat', 'rabbit', 'bird', 'other']
        if data.get('animal_type') and data['animal_type'].lower() not in valid_types:
            warnings.append(f"Unusual animal type: {data['animal_type']}")

        # Validate age format
        if data.get('age'):
            age = data['age']
            if not any(x in age.lower() for x in ['year', 'month', 'week', 'puppy', 'kitten', 'adult', 'senior']):
                warnings.append("Age format may need standardization")

        # Validate shelter exists
        if data.get('shelter_id'):
            shelter_exists = await self.request_from_agent(
                'librarian', 'get_shelter', {'shelter_id': data['shelter_id']}
            )
            if not shelter_exists or shelter_exists.get('error'):
                errors.append(f"Invalid shelter_id: {data['shelter_id']}")

        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}

    async def enrich_profile(self, data: Dict) -> Dict:
        """Enrich animal profile with additional data"""
        enrichments = {}

        # Get breed info if available
        if data.get('breed'):
            breed_info = await self.request_from_agent(
                'librarian', 'get_breed_info', {'breed': data['breed']}
            )
            if breed_info and not breed_info.get('error'):
                enrichments['breed_info'] = breed_info

        # Estimate age category
        enrichments['age_category'] = self._categorize_age(data.get('age', ''))

        # Add intake date if not present
        if not data.get('intake_date'):
            enrichments['intake_date'] = datetime.now().date().isoformat()

        # Calculate initial waiting time
        enrichments['days_waiting'] = 0

        return enrichments

    async def detect_duplicates(self, data: Dict) -> Dict:
        """Detect potential duplicate entries"""
        duplicates = []

        # Search for similar animals
        search_result = await self.request_from_agent(
            'librarian', 'search', {
                'query': data.get('name', ''),
                'category': 'animal'
            }
        )

        if search_result and search_result.get('results'):
            for result in search_result['results']:
                # Simple similarity check
                if result.get('title', '').lower() == data.get('name', '').lower():
                    duplicates.append({
                        'entry_id': result['entry_id'],
                        'title': result['title'],
                        'confidence': 0.9
                    })

        return {'duplicates': duplicates, 'count': len(duplicates)}

    def _categorize_age(self, age_str: str) -> str:
        """Categorize age into standard groups"""
        age_lower = age_str.lower()

        if any(x in age_lower for x in ['puppy', 'kitten', 'baby', 'week', 'newborn']):
            return 'baby'
        if any(x in age_lower for x in ['young', 'junior', '1 year', '2 year']):
            return 'young'
        if any(x in age_lower for x in ['senior', 'elder', '10', '11', '12', '13', '14', '15']):
            return 'senior'
        return 'adult'

    async def _save_animal(self, intake: IntakeRecord) -> bool:
        """Save animal to database"""
        try:
            db = self.get_db()
            from app.models import Animal

            animal = Animal(
                name=intake.animal_data.get('name'),
                animal_type=intake.animal_data.get('animal_type', 'dog'),
                breed=intake.animal_data.get('breed'),
                age=intake.animal_data.get('age'),
                gender=intake.animal_data.get('gender'),
                size=intake.animal_data.get('size'),
                description=intake.animal_data.get('description'),
                shelter_id=intake.animal_data.get('shelter_id'),
                intake_date=datetime.now().date(),
                photo_url=intake.animal_data.get('photo_url'),
                status='available'
            )

            db.add(animal)
            db.commit()
            db.close()
            return True

        except Exception as e:
            self.logger.error(f"Failed to save animal: {e}")
            return False

    async def batch_intake(self, animals: List[Dict]) -> Dict:
        """Process multiple intakes"""
        results = {'processed': 0, 'failed': 0, 'details': []}

        for animal in animals:
            result = await self.process_intake(animal)
            if result.get('status') == 'complete':
                results['processed'] += 1
            else:
                results['failed'] += 1
            results['details'].append(result)

        return results

    async def _handle_intake(self, payload: Dict) -> Dict:
        return await self.process_intake(payload)

    async def _handle_validate(self, payload: Dict) -> Dict:
        return await self.validate_data(payload)

    async def _handle_enrich(self, payload: Dict) -> Dict:
        return await self.enrich_profile(payload)

    async def _handle_pending(self, payload: Dict) -> Dict:
        return {'pending': len(self.intake_queue), 'processed': len(self.processed)}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Intake Specialist Agent CLI")
    parser.add_argument('--intake', type=str, help='Process intake with JSON data')
    parser.add_argument('--validate', type=str, help='Validate data')

    args = parser.parse_args()
    agent = IntakeSpecialistAgent()

    if args.intake:
        data = json.loads(args.intake)
        result = asyncio.run(agent.process_intake(data))
        print(json.dumps(result, indent=2))
    elif args.validate:
        data = json.loads(args.validate)
        result = asyncio.run(agent.validate_data(data))
        print(json.dumps(result, indent=2))
