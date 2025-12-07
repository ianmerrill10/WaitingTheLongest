#!/usr/bin/env python3
"""
===============================================================================
Librarian Agent - Knowledge & Data Library Manager
===============================================================================
Manages the knowledge library, provides data lookups, and maintains the
central repository of all system information.

Features:
- Animal profile management
- Breed information lookup
- Shelter data access
- Historical data archival
- Search and retrieval
- Data caching
- Cross-reference management
- Knowledge graph maintenance

Cooperates with: ALL agents (central knowledge hub)
===============================================================================
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agents.base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority
from agents.protocols import CooperativeMixin, DataCategory, Priority


@dataclass
class KnowledgeEntry:
    """A knowledge library entry"""
    entry_id: str
    category: str  # breed, animal, shelter, health, training
    title: str
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    source: str = "system"


class LibrarianAgent(CooperativeMixin, BaseAgent):
    """
    Central knowledge and data library manager.

    Commands:
    - get_animal: Get animal profile by ID
    - get_breed_info: Get breed information
    - get_shelter: Get shelter information
    - search: Search the knowledge library
    - add_entry: Add new knowledge entry
    - update_entry: Update existing entry
    - get_statistics: Get library statistics
    - get_longest_waiting: Get longest waiting animals
    - archive: Archive old entries
    """

    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="librarian",
            agent_name="Librarian Agent",
            agent_type="specialized_agent",
            description="Knowledge and data library manager"
        )
        CooperativeMixin.__init__(self)

        self.knowledge_base: Dict[str, KnowledgeEntry] = {}
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}

        # Register handlers for ALL agents to use
        self.register_handler('get_animal', self._handle_get_animal)
        self.register_handler('get_animal_profile', self._handle_get_animal)
        self.register_handler('get_breed_info', self._handle_get_breed)
        self.register_handler('get_shelter', self._handle_get_shelter)
        self.register_handler('search', self._handle_search)
        self.register_handler('get_longest_waiting', self._handle_longest_waiting)
        self.register_handler('add_knowledge', self._handle_add_knowledge)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a librarian task"""
        task.started_at = datetime.now()

        try:
            if task.task_type == "get_animal":
                result = await self.get_animal(task.payload.get('animal_id'))
            elif task.task_type == "get_breed_info":
                result = await self.get_breed_info(task.payload.get('breed'))
            elif task.task_type == "search":
                result = await self.search(task.payload)
            elif task.task_type == "get_statistics":
                result = await self.get_statistics()
            elif task.task_type == "refresh_cache":
                result = await self.refresh_cache()
            else:
                result = {'error': f"Unknown task type: {task.task_type}"}

            task.completed_at = datetime.now()
            return AgentResult(
                success=True,
                message=f"Librarian task completed: {task.task_type}",
                data=result,
                duration_seconds=(task.completed_at - task.started_at).total_seconds()
            )

        except Exception as e:
            self.logger.error(f"Librarian task failed: {e}", exc_info=True)
            return AgentResult(success=False, message=str(e), errors=[str(e)])

    async def run(self) -> AgentResult:
        """Main librarian agent loop"""
        self.logger.info("Librarian Agent starting")
        processed = 0

        # Load initial data
        await self.refresh_cache()

        while self.status.value == "running":
            await self.process_messages()

            task = self.get_next_task()
            if task:
                await self.execute_task(task)
                processed += 1
            else:
                await asyncio.sleep(1)

        return AgentResult(success=True, message="Librarian Agent completed", items_processed=processed)

    async def get_animal(self, animal_id: int) -> Optional[Dict]:
        """Get animal profile from database"""
        cache_key = f"animal_{animal_id}"

        # Check cache first
        if cache_key in self.cache:
            if self.cache_ttl.get(cache_key, datetime.min) > datetime.now():
                self.logger.debug(f"Cache hit for animal {animal_id}")
                return self.cache[cache_key]

        # Query database
        try:
            db = self.get_db()
            from app.models import Animal
            animal = db.query(Animal).filter(Animal.id == animal_id).first()

            if animal:
                profile = {
                    'id': animal.id,
                    'name': animal.name,
                    'type': animal.animal_type,
                    'breed': animal.breed,
                    'age': animal.age,
                    'gender': animal.gender,
                    'size': animal.size,
                    'description': animal.description,
                    'shelter_id': animal.shelter_id,
                    'intake_date': animal.intake_date.isoformat() if animal.intake_date else None,
                    'days_waiting': (datetime.now().date() - animal.intake_date).days if animal.intake_date else 0,
                    'photo_url': animal.photo_url,
                    'status': animal.status
                }

                # Cache the result
                self.cache[cache_key] = profile
                self.cache_ttl[cache_key] = datetime.now() + timedelta(hours=1)

                db.close()
                return profile

            db.close()
        except Exception as e:
            self.logger.error(f"Error getting animal: {e}")

        return None

    async def get_breed_info(self, breed: str) -> Optional[Dict]:
        """Get breed information from knowledge base"""
        cache_key = f"breed_{breed.lower()}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            db = self.get_db()
            from app.models import DogBreed
            breed_info = db.query(DogBreed).filter(
                DogBreed.name.ilike(f"%{breed}%")
            ).first()

            if breed_info:
                info = {
                    'id': breed_info.id,
                    'name': breed_info.name,
                    'breed_group': breed_info.breed_group,
                    'origin': breed_info.origin,
                    'life_span': breed_info.life_span,
                    'temperament': breed_info.temperament,
                    'description': breed_info.description,
                    'weight': breed_info.weight,
                    'height': breed_info.height,
                    'image_url': breed_info.image_url
                }

                self.cache[cache_key] = info
                db.close()
                return info

            db.close()
        except Exception as e:
            self.logger.error(f"Error getting breed info: {e}")

        return None

    async def get_shelter(self, shelter_id: int) -> Optional[Dict]:
        """Get shelter information"""
        cache_key = f"shelter_{shelter_id}"

        if cache_key in self.cache:
            if self.cache_ttl.get(cache_key, datetime.min) > datetime.now():
                return self.cache[cache_key]

        try:
            db = self.get_db()
            from app.models import Shelter
            shelter = db.query(Shelter).filter(Shelter.id == shelter_id).first()

            if shelter:
                info = {
                    'id': shelter.id,
                    'name': shelter.name,
                    'city': shelter.city,
                    'state': shelter.state,
                    'address': shelter.address,
                    'phone': shelter.phone,
                    'email': shelter.email,
                    'website': shelter.website,
                    'animal_count': len(shelter.animals) if hasattr(shelter, 'animals') else 0
                }

                self.cache[cache_key] = info
                self.cache_ttl[cache_key] = datetime.now() + timedelta(hours=6)

                db.close()
                return info

            db.close()
        except Exception as e:
            self.logger.error(f"Error getting shelter: {e}")

        return None

    async def search(self, params: Dict) -> List[Dict]:
        """Search the knowledge library"""
        query = params.get('query', '')
        category = params.get('category')
        limit = params.get('limit', 20)

        results = []

        # Search knowledge base
        for entry_id, entry in self.knowledge_base.items():
            if category and entry.category != category:
                continue

            if query.lower() in entry.title.lower():
                results.append({
                    'entry_id': entry_id,
                    'category': entry.category,
                    'title': entry.title,
                    'relevance': 1.0
                })
                entry.access_count += 1

        # Also search database for animals/shelters
        try:
            db = self.get_db()
            from app.models import Animal, Shelter

            if not category or category == 'animal':
                animals = db.query(Animal).filter(
                    Animal.name.ilike(f"%{query}%")
                ).limit(limit).all()

                for animal in animals:
                    results.append({
                        'entry_id': f"animal_{animal.id}",
                        'category': 'animal',
                        'title': animal.name,
                        'relevance': 0.9
                    })

            if not category or category == 'shelter':
                shelters = db.query(Shelter).filter(
                    Shelter.name.ilike(f"%{query}%")
                ).limit(limit).all()

                for shelter in shelters:
                    results.append({
                        'entry_id': f"shelter_{shelter.id}",
                        'category': 'shelter',
                        'title': shelter.name,
                        'relevance': 0.8
                    })

            db.close()
        except Exception as e:
            self.logger.error(f"Search error: {e}")

        return sorted(results, key=lambda x: x['relevance'], reverse=True)[:limit]

    async def get_longest_waiting(self, params: Dict) -> List[Dict]:
        """Get animals waiting the longest"""
        limit = params.get('limit', 10)
        animal_type = params.get('type')
        state = params.get('state')

        try:
            db = self.get_db()
            from app.models import Animal, Shelter
            from sqlalchemy import desc

            query = db.query(Animal).filter(Animal.status == 'available')

            if animal_type:
                query = query.filter(Animal.animal_type == animal_type)

            if state:
                query = query.join(Shelter).filter(Shelter.state == state)

            query = query.filter(Animal.intake_date.isnot(None))
            query = query.order_by(Animal.intake_date.asc())

            animals = query.limit(limit).all()

            results = []
            for animal in animals:
                days = (datetime.now().date() - animal.intake_date).days if animal.intake_date else 0
                results.append({
                    'id': animal.id,
                    'name': animal.name,
                    'type': animal.animal_type,
                    'breed': animal.breed,
                    'days_waiting': days,
                    'intake_date': animal.intake_date.isoformat() if animal.intake_date else None,
                    'shelter_id': animal.shelter_id,
                    'photo_url': animal.photo_url
                })

            db.close()
            return results

        except Exception as e:
            self.logger.error(f"Error getting longest waiting: {e}")
            return []

    async def get_statistics(self) -> Dict:
        """Get library statistics"""
        try:
            db = self.get_db()
            from app.models import Animal, Shelter, DogBreed

            stats = {
                'total_animals': db.query(Animal).count(),
                'available_animals': db.query(Animal).filter(Animal.status == 'available').count(),
                'total_shelters': db.query(Shelter).count(),
                'total_breeds': db.query(DogBreed).count(),
                'knowledge_entries': len(self.knowledge_base),
                'cache_size': len(self.cache),
                'last_updated': datetime.now().isoformat()
            }

            db.close()
            return stats

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}

    async def refresh_cache(self) -> Dict:
        """Refresh cached data"""
        expired = []
        now = datetime.now()

        for key, ttl in list(self.cache_ttl.items()):
            if ttl < now:
                expired.append(key)
                del self.cache[key]
                del self.cache_ttl[key]

        self.logger.info(f"Cache refreshed, {len(expired)} entries expired")
        return {'expired': len(expired), 'remaining': len(self.cache)}

    async def add_knowledge(self, data: Dict) -> Dict:
        """Add a new knowledge entry"""
        entry = KnowledgeEntry(
            entry_id=f"kb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            category=data.get('category', 'general'),
            title=data.get('title', 'Untitled'),
            content=data.get('content', {}),
            tags=data.get('tags', []),
            source=data.get('source', 'system')
        )

        self.knowledge_base[entry.entry_id] = entry

        return {'entry_id': entry.entry_id, 'status': 'added'}

    # Handler methods for cooperation
    async def _handle_get_animal(self, payload: Dict) -> Dict:
        animal_id = payload.get('animal_id')
        result = await self.get_animal(animal_id)
        return result or {'error': 'Animal not found'}

    async def _handle_get_breed(self, payload: Dict) -> Dict:
        breed = payload.get('breed')
        result = await self.get_breed_info(breed)
        return result or {'error': 'Breed not found'}

    async def _handle_get_shelter(self, payload: Dict) -> Dict:
        shelter_id = payload.get('shelter_id')
        result = await self.get_shelter(shelter_id)
        return result or {'error': 'Shelter not found'}

    async def _handle_search(self, payload: Dict) -> Dict:
        results = await self.search(payload)
        return {'results': results, 'count': len(results)}

    async def _handle_longest_waiting(self, payload: Dict) -> Dict:
        results = await self.get_longest_waiting(payload)
        return {'animals': results, 'count': len(results)}

    async def _handle_add_knowledge(self, payload: Dict) -> Dict:
        return await self.add_knowledge(payload)


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Librarian Agent CLI")
    parser.add_argument('--stats', action='store_true', help='Get library statistics')
    parser.add_argument('--longest', type=int, default=10, help='Get N longest waiting animals')
    parser.add_argument('--search', type=str, help='Search query')
    parser.add_argument('--animal', type=int, help='Get animal by ID')
    parser.add_argument('--breed', type=str, help='Get breed info')

    args = parser.parse_args()
    agent = LibrarianAgent()

    if args.stats:
        result = asyncio.run(agent.get_statistics())
        print(json.dumps(result, indent=2))
    elif args.longest:
        result = asyncio.run(agent.get_longest_waiting({'limit': args.longest}))
        print(json.dumps(result, indent=2))
    elif args.search:
        result = asyncio.run(agent.search({'query': args.search}))
        print(json.dumps(result, indent=2))
    elif args.animal:
        result = asyncio.run(agent.get_animal(args.animal))
        print(json.dumps(result, indent=2))
    elif args.breed:
        result = asyncio.run(agent.get_breed_info(args.breed))
        print(json.dumps(result, indent=2))
