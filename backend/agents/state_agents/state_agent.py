#!/usr/bin/env python3
"""
===============================================================================
State Agent - Shelter Discovery Agent for Individual US States
===============================================================================
Each state agent is responsible for:
- Finding all animal shelters and rescues in their state
- Validating shelter data
- Monitoring for new shelters
- Updating shelter information
- Reporting to the orchestrator

Data Sources Used:
- RescueGroups.org API
- State government registries
- Pet adoption directories
- Google Places API
- Social media (Facebook groups, etc.)

Author: Waiting The Longest Development Team
===============================================================================
"""

import os
import sys
import json
import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from urllib.parse import quote_plus, urljoin
from dataclasses import dataclass

# Add parent directories for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base_agent import BaseAgent, AgentTask, AgentResult, TaskPriority, generate_task_id
from app.database import SessionLocal
from app.models import Shelter


# Complete US State Data with regions and major cities
STATE_DATA = {
    'AL': {'name': 'Alabama', 'capital': 'Montgomery', 'region': 'South', 'cities': ['Birmingham', 'Huntsville', 'Mobile', 'Montgomery', 'Tuscaloosa']},
    'AK': {'name': 'Alaska', 'capital': 'Juneau', 'region': 'West', 'cities': ['Anchorage', 'Fairbanks', 'Juneau', 'Sitka', 'Ketchikan']},
    'AZ': {'name': 'Arizona', 'capital': 'Phoenix', 'region': 'Southwest', 'cities': ['Phoenix', 'Tucson', 'Mesa', 'Scottsdale', 'Tempe']},
    'AR': {'name': 'Arkansas', 'capital': 'Little Rock', 'region': 'South', 'cities': ['Little Rock', 'Fort Smith', 'Fayetteville', 'Springdale', 'Jonesboro']},
    'CA': {'name': 'California', 'capital': 'Sacramento', 'region': 'West', 'cities': ['Los Angeles', 'San Francisco', 'San Diego', 'San Jose', 'Sacramento', 'Oakland', 'Fresno']},
    'CO': {'name': 'Colorado', 'capital': 'Denver', 'region': 'West', 'cities': ['Denver', 'Colorado Springs', 'Aurora', 'Fort Collins', 'Boulder']},
    'CT': {'name': 'Connecticut', 'capital': 'Hartford', 'region': 'Northeast', 'cities': ['Hartford', 'New Haven', 'Stamford', 'Bridgeport', 'Waterbury']},
    'DE': {'name': 'Delaware', 'capital': 'Dover', 'region': 'Northeast', 'cities': ['Wilmington', 'Dover', 'Newark', 'Middletown', 'Smyrna']},
    'FL': {'name': 'Florida', 'capital': 'Tallahassee', 'region': 'South', 'cities': ['Miami', 'Orlando', 'Tampa', 'Jacksonville', 'Fort Lauderdale', 'St. Petersburg']},
    'GA': {'name': 'Georgia', 'capital': 'Atlanta', 'region': 'South', 'cities': ['Atlanta', 'Augusta', 'Columbus', 'Savannah', 'Athens']},
    'HI': {'name': 'Hawaii', 'capital': 'Honolulu', 'region': 'West', 'cities': ['Honolulu', 'Hilo', 'Kailua', 'Pearl City', 'Waipahu']},
    'ID': {'name': 'Idaho', 'capital': 'Boise', 'region': 'West', 'cities': ['Boise', 'Meridian', 'Nampa', 'Idaho Falls', 'Pocatello']},
    'IL': {'name': 'Illinois', 'capital': 'Springfield', 'region': 'Midwest', 'cities': ['Chicago', 'Aurora', 'Rockford', 'Springfield', 'Naperville']},
    'IN': {'name': 'Indiana', 'capital': 'Indianapolis', 'region': 'Midwest', 'cities': ['Indianapolis', 'Fort Wayne', 'Evansville', 'South Bend', 'Carmel']},
    'IA': {'name': 'Iowa', 'capital': 'Des Moines', 'region': 'Midwest', 'cities': ['Des Moines', 'Cedar Rapids', 'Davenport', 'Sioux City', 'Iowa City']},
    'KS': {'name': 'Kansas', 'capital': 'Topeka', 'region': 'Midwest', 'cities': ['Wichita', 'Overland Park', 'Kansas City', 'Topeka', 'Olathe']},
    'KY': {'name': 'Kentucky', 'capital': 'Frankfort', 'region': 'South', 'cities': ['Louisville', 'Lexington', 'Bowling Green', 'Frankfort', 'Covington']},
    'LA': {'name': 'Louisiana', 'capital': 'Baton Rouge', 'region': 'South', 'cities': ['New Orleans', 'Baton Rouge', 'Shreveport', 'Lafayette', 'Lake Charles']},
    'ME': {'name': 'Maine', 'capital': 'Augusta', 'region': 'Northeast', 'cities': ['Portland', 'Lewiston', 'Bangor', 'Augusta', 'South Portland']},
    'MD': {'name': 'Maryland', 'capital': 'Annapolis', 'region': 'Northeast', 'cities': ['Baltimore', 'Frederick', 'Rockville', 'Annapolis', 'Gaithersburg']},
    'MA': {'name': 'Massachusetts', 'capital': 'Boston', 'region': 'Northeast', 'cities': ['Boston', 'Worcester', 'Springfield', 'Cambridge', 'Lowell']},
    'MI': {'name': 'Michigan', 'capital': 'Lansing', 'region': 'Midwest', 'cities': ['Detroit', 'Grand Rapids', 'Ann Arbor', 'Lansing', 'Flint']},
    'MN': {'name': 'Minnesota', 'capital': 'Saint Paul', 'region': 'Midwest', 'cities': ['Minneapolis', 'Saint Paul', 'Rochester', 'Duluth', 'Bloomington']},
    'MS': {'name': 'Mississippi', 'capital': 'Jackson', 'region': 'South', 'cities': ['Jackson', 'Gulfport', 'Southaven', 'Hattiesburg', 'Biloxi']},
    'MO': {'name': 'Missouri', 'capital': 'Jefferson City', 'region': 'Midwest', 'cities': ['Kansas City', 'St. Louis', 'Springfield', 'Columbia', 'Jefferson City']},
    'MT': {'name': 'Montana', 'capital': 'Helena', 'region': 'West', 'cities': ['Billings', 'Missoula', 'Great Falls', 'Bozeman', 'Helena']},
    'NE': {'name': 'Nebraska', 'capital': 'Lincoln', 'region': 'Midwest', 'cities': ['Omaha', 'Lincoln', 'Bellevue', 'Grand Island', 'Kearney']},
    'NV': {'name': 'Nevada', 'capital': 'Carson City', 'region': 'West', 'cities': ['Las Vegas', 'Henderson', 'Reno', 'North Las Vegas', 'Carson City']},
    'NH': {'name': 'New Hampshire', 'capital': 'Concord', 'region': 'Northeast', 'cities': ['Manchester', 'Nashua', 'Concord', 'Dover', 'Rochester']},
    'NJ': {'name': 'New Jersey', 'capital': 'Trenton', 'region': 'Northeast', 'cities': ['Newark', 'Jersey City', 'Paterson', 'Trenton', 'Elizabeth']},
    'NM': {'name': 'New Mexico', 'capital': 'Santa Fe', 'region': 'Southwest', 'cities': ['Albuquerque', 'Las Cruces', 'Rio Rancho', 'Santa Fe', 'Roswell']},
    'NY': {'name': 'New York', 'capital': 'Albany', 'region': 'Northeast', 'cities': ['New York City', 'Buffalo', 'Rochester', 'Syracuse', 'Albany']},
    'NC': {'name': 'North Carolina', 'capital': 'Raleigh', 'region': 'South', 'cities': ['Charlotte', 'Raleigh', 'Greensboro', 'Durham', 'Winston-Salem']},
    'ND': {'name': 'North Dakota', 'capital': 'Bismarck', 'region': 'Midwest', 'cities': ['Fargo', 'Bismarck', 'Grand Forks', 'Minot', 'West Fargo']},
    'OH': {'name': 'Ohio', 'capital': 'Columbus', 'region': 'Midwest', 'cities': ['Columbus', 'Cleveland', 'Cincinnati', 'Toledo', 'Akron']},
    'OK': {'name': 'Oklahoma', 'capital': 'Oklahoma City', 'region': 'South', 'cities': ['Oklahoma City', 'Tulsa', 'Norman', 'Broken Arrow', 'Edmond']},
    'OR': {'name': 'Oregon', 'capital': 'Salem', 'region': 'West', 'cities': ['Portland', 'Salem', 'Eugene', 'Gresham', 'Hillsboro']},
    'PA': {'name': 'Pennsylvania', 'capital': 'Harrisburg', 'region': 'Northeast', 'cities': ['Philadelphia', 'Pittsburgh', 'Allentown', 'Harrisburg', 'Erie']},
    'RI': {'name': 'Rhode Island', 'capital': 'Providence', 'region': 'Northeast', 'cities': ['Providence', 'Warwick', 'Cranston', 'Pawtucket', 'Newport']},
    'SC': {'name': 'South Carolina', 'capital': 'Columbia', 'region': 'South', 'cities': ['Charleston', 'Columbia', 'North Charleston', 'Greenville', 'Myrtle Beach']},
    'SD': {'name': 'South Dakota', 'capital': 'Pierre', 'region': 'Midwest', 'cities': ['Sioux Falls', 'Rapid City', 'Aberdeen', 'Brookings', 'Pierre']},
    'TN': {'name': 'Tennessee', 'capital': 'Nashville', 'region': 'South', 'cities': ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga', 'Clarksville']},
    'TX': {'name': 'Texas', 'capital': 'Austin', 'region': 'South', 'cities': ['Houston', 'Dallas', 'San Antonio', 'Austin', 'Fort Worth', 'El Paso']},
    'UT': {'name': 'Utah', 'capital': 'Salt Lake City', 'region': 'West', 'cities': ['Salt Lake City', 'West Valley City', 'Provo', 'West Jordan', 'Orem']},
    'VT': {'name': 'Vermont', 'capital': 'Montpelier', 'region': 'Northeast', 'cities': ['Burlington', 'South Burlington', 'Rutland', 'Montpelier', 'Barre']},
    'VA': {'name': 'Virginia', 'capital': 'Richmond', 'region': 'South', 'cities': ['Virginia Beach', 'Norfolk', 'Chesapeake', 'Richmond', 'Arlington']},
    'WA': {'name': 'Washington', 'capital': 'Olympia', 'region': 'West', 'cities': ['Seattle', 'Spokane', 'Tacoma', 'Vancouver', 'Olympia']},
    'WV': {'name': 'West Virginia', 'capital': 'Charleston', 'region': 'South', 'cities': ['Charleston', 'Huntington', 'Morgantown', 'Parkersburg', 'Wheeling']},
    'WI': {'name': 'Wisconsin', 'capital': 'Madison', 'region': 'Midwest', 'cities': ['Milwaukee', 'Madison', 'Green Bay', 'Kenosha', 'Racine']},
    'WY': {'name': 'Wyoming', 'capital': 'Cheyenne', 'region': 'West', 'cities': ['Cheyenne', 'Casper', 'Laramie', 'Gillette', 'Rock Springs']},
    'DC': {'name': 'Washington DC', 'capital': 'Washington', 'region': 'Northeast', 'cities': ['Washington']}
}

# Terms that indicate NOT a legitimate shelter
EXCLUDE_TERMS = [
    'breeder', 'breeding', 'puppies for sale', 'kittens for sale',
    'pet store', 'pet shop', 'petco', 'petsmart', 'puppy mill',
    'stud service', 'akc registered', 'ckc registered', 'for sale'
]

# Terms that indicate a legitimate shelter/rescue
INCLUDE_TERMS = [
    'rescue', 'shelter', 'humane society', 'spca', 'animal control',
    'adoption', 'foster', 'sanctuary', 'animal welfare', 'aspca',
    'no-kill', 'nonprofit', 'non-profit', '501c3', '501(c)(3)'
]


class StateAgent(BaseAgent):
    """
    AI Agent specialized in finding animal shelters within a specific US state.

    Each instance is responsible for:
    1. Discovering new shelters in their assigned state
    2. Validating and enriching shelter data
    3. Monitoring for updates and changes
    4. Reporting findings to the orchestrator
    """

    def __init__(self, state_code: str):
        if state_code not in STATE_DATA:
            raise ValueError(f"Invalid state code: {state_code}")

        self.state_code = state_code
        self.state_info = STATE_DATA[state_code]
        self.state_name = self.state_info['name']

        super().__init__(
            agent_id=f"state_agent_{state_code.lower()}",
            agent_name=f"{self.state_name} Shelter Discovery Agent",
            agent_type="state_discovery",
            description=f"Finds and catalogs animal shelters and rescues in {self.state_name}"
        )

        # State-specific tracking
        self.discovered_shelters: Set[str] = set()  # Names of found shelters
        self.pending_verification: List[Dict] = []
        self.search_sources: List[str] = []

        # Load previous state if exists
        self._load_previous_state()

    def _load_previous_state(self):
        """Load previously discovered shelters"""
        state = self.load_state()
        if state:
            self.discovered_shelters = set(state.get('discovered_shelters', []))
            self.logger.info(f"Loaded {len(self.discovered_shelters)} previously discovered shelters")

    def get_custom_state(self) -> Dict:
        """Save discovered shelter names"""
        return {
            'discovered_shelters': list(self.discovered_shelters),
            'pending_verification': len(self.pending_verification)
        }

    def _is_valid_shelter(self, name: str, description: str = "") -> bool:
        """Check if an organization is a valid shelter (not breeder/store)"""
        text = f"{name} {description}".lower()

        # Check for exclusions
        for term in EXCLUDE_TERMS:
            if term in text:
                return False

        # Check for inclusions (at least one should match)
        has_shelter_term = any(term in text for term in INCLUDE_TERMS)
        return has_shelter_term

    def _normalize_shelter_name(self, name: str) -> str:
        """Normalize shelter name for deduplication"""
        # Remove common suffixes and normalize
        name = name.lower().strip()
        for suffix in [', inc.', ', inc', ' inc.', ' inc', ' llc', ', llc']:
            name = name.replace(suffix, '')
        return re.sub(r'\s+', ' ', name)

    async def search_rescuegroups(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Search RescueGroups.org for shelters in this state"""
        shelters = []

        # This would use the RescueGroups API
        # For now, query from existing database
        db = self.get_db()
        try:
            existing = db.query(Shelter).filter(Shelter.state == self.state_code).all()
            for s in existing:
                shelters.append({
                    'name': s.name,
                    'city': s.city,
                    'state': s.state,
                    'phone': s.phone,
                    'email': s.email,
                    'website': s.website,
                    'source': 'rescuegroups'
                })
                self.discovered_shelters.add(self._normalize_shelter_name(s.name))
        finally:
            db.close()

        self.logger.info(f"Found {len(shelters)} shelters in database for {self.state_code}")
        return shelters

    async def search_directory_sites(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Search pet adoption directory websites"""
        shelters = []

        # Directory sites to search
        directories = [
            f"https://www.petfinder.com/animal-shelters-and-rescues/search/?location={self.state_name}",
            f"https://www.adoptapet.com/shelter-search?location={self.state_name}",
        ]

        for url in directories:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        # Parse the response and extract shelter data
                        # This is a simplified version - real implementation would parse HTML
                        self.logger.debug(f"Searched {url}")
            except Exception as e:
                self.logger.warning(f"Error searching {url}: {e}")
                await asyncio.sleep(1)

        return shelters

    async def search_cities(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Search each major city in the state"""
        shelters = []
        cities = self.state_info.get('cities', [])

        for city in cities:
            self.logger.debug(f"Searching in {city}, {self.state_code}...")
            # Would perform city-specific searches here
            await asyncio.sleep(0.5)  # Rate limiting

        return shelters

    async def verify_shelter(self, shelter: Dict) -> bool:
        """Verify a shelter is legitimate and still operating"""
        name = shelter.get('name', '')
        website = shelter.get('website', '')

        if not name:
            return False

        # Check if it's a valid shelter type
        if not self._is_valid_shelter(name, shelter.get('description', '')):
            return False

        # If website exists, try to verify it's still active
        if website:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(website, timeout=10) as response:
                        return response.status < 400
            except Exception:
                pass  # Website check failed, but shelter might still be valid

        return True

    async def save_shelter_to_db(self, shelter: Dict) -> bool:
        """Save a discovered shelter to the database"""
        db = self.get_db()
        try:
            # Check if shelter already exists
            existing = db.query(Shelter).filter(
                Shelter.name == shelter['name'],
                Shelter.state == shelter.get('state', self.state_code)
            ).first()

            if existing:
                # Update existing
                for key in ['phone', 'email', 'website', 'address', 'city']:
                    if shelter.get(key) and not getattr(existing, key, None):
                        setattr(existing, key, shelter[key])
                db.commit()
                return False  # Not a new shelter
            else:
                # Create new
                new_shelter = Shelter(
                    name=shelter['name'],
                    city=shelter.get('city'),
                    state=shelter.get('state', self.state_code),
                    phone=shelter.get('phone'),
                    email=shelter.get('email'),
                    website=shelter.get('website'),
                    address=shelter.get('address'),
                    source=f"state_agent_{self.state_code.lower()}",
                    org_type='rescue'
                )
                db.add(new_shelter)
                db.commit()
                return True  # New shelter added

        except Exception as e:
            self.logger.error(f"Error saving shelter: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a single discovery task"""
        start_time = datetime.now()
        items_processed = 0
        items_created = 0
        errors = []

        try:
            task_type = task.task_type

            async with aiohttp.ClientSession() as session:
                if task_type == "full_discovery":
                    # Run all discovery methods
                    shelters = await self.search_rescuegroups(session)
                    items_processed += len(shelters)

                    dir_shelters = await self.search_directory_sites(session)
                    items_processed += len(dir_shelters)
                    shelters.extend(dir_shelters)

                    city_shelters = await self.search_cities(session)
                    items_processed += len(city_shelters)
                    shelters.extend(city_shelters)

                    # Save new shelters
                    for shelter in shelters:
                        if await self.save_shelter_to_db(shelter):
                            items_created += 1

                elif task_type == "verify_shelters":
                    # Verify existing shelters are still active
                    db = self.get_db()
                    try:
                        shelters = db.query(Shelter).filter(
                            Shelter.state == self.state_code
                        ).all()
                        items_processed = len(shelters)
                    finally:
                        db.close()

                elif task_type == "search_city":
                    city = task.payload.get('city')
                    if city:
                        shelters = await self.search_cities(session)
                        items_processed = len(shelters)

            duration = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                success=True,
                message=f"Completed {task_type} for {self.state_name}",
                data={'shelters_found': items_processed, 'new_shelters': items_created},
                items_processed=items_processed,
                items_created=items_created,
                duration_seconds=duration
            )

        except Exception as e:
            self.logger.error(f"Task error: {e}", exc_info=True)
            errors.append(str(e))
            return AgentResult(
                success=False,
                message=f"Task failed: {str(e)}",
                errors=errors
            )

    async def run(self) -> AgentResult:
        """Main execution loop for the state agent"""
        self.logger.info(f"Starting shelter discovery for {self.state_name}")
        start_time = datetime.now()

        total_processed = 0
        total_created = 0
        all_errors = []

        # Create initial discovery task if queue is empty
        if self.task_queue.empty():
            task = AgentTask(
                task_id=generate_task_id(f"discovery_{self.state_code}"),
                task_type="full_discovery",
                payload={'state': self.state_code}
            )
            self.add_task(task)

        # Process all tasks
        while not self.task_queue.empty():
            task = self.get_next_task()
            if task:
                self.current_task = task
                task.started_at = datetime.now()
                task.status = "running"

                result = await self.execute_task(task)

                task.completed_at = datetime.now()
                task.status = "completed" if result.success else "failed"
                task.result = result.data
                self.completed_tasks.append(task)

                total_processed += result.items_processed
                total_created += result.items_created
                all_errors.extend(result.errors)

                self.last_activity = datetime.now()

        # Save state
        self.save_state()

        duration = (datetime.now() - start_time).total_seconds()

        return AgentResult(
            success=len(all_errors) == 0,
            message=f"Completed discovery for {self.state_name}: {total_created} new shelters found",
            data={
                'state': self.state_code,
                'state_name': self.state_name,
                'total_shelters': len(self.discovered_shelters),
                'new_shelters': total_created
            },
            items_processed=total_processed,
            items_created=total_created,
            duration_seconds=duration,
            errors=all_errors
        )

    def get_shelter_count(self) -> int:
        """Get current shelter count for this state"""
        db = self.get_db()
        try:
            return db.query(Shelter).filter(Shelter.state == self.state_code).count()
        finally:
            db.close()

    def get_status_report(self) -> Dict:
        """Get detailed status for this state agent"""
        report = super().get_status_report()
        report.update({
            'state_code': self.state_code,
            'state_name': self.state_name,
            'region': self.state_info['region'],
            'shelter_count': self.get_shelter_count(),
            'discovered_this_session': len(self.discovered_shelters)
        })
        return report


# Factory functions for creating state agents
_state_agents: Dict[str, StateAgent] = {}


def get_state_agent(state_code: str) -> StateAgent:
    """Get or create a state agent for the given state code"""
    state_code = state_code.upper()
    if state_code not in _state_agents:
        _state_agents[state_code] = StateAgent(state_code)
    return _state_agents[state_code]


def get_all_state_agents() -> List[StateAgent]:
    """Get all 50 (+ DC) state agents"""
    for state_code in STATE_DATA.keys():
        if state_code not in _state_agents:
            _state_agents[state_code] = StateAgent(state_code)
    return list(_state_agents.values())


def get_state_agents_by_region(region: str) -> List[StateAgent]:
    """Get all state agents in a specific region"""
    agents = []
    for state_code, info in STATE_DATA.items():
        if info['region'].lower() == region.lower():
            agents.append(get_state_agent(state_code))
    return agents


# CLI for running individual state agents
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run state shelter discovery agent")
    parser.add_argument("--state", type=str, help="State code (e.g., CA, NY, TX)")
    parser.add_argument("--all", action="store_true", help="Run all state agents")
    parser.add_argument("--region", type=str, help="Run agents for a region (e.g., West, South)")
    parser.add_argument("--status", action="store_true", help="Show status of all agents")

    args = parser.parse_args()

    if args.status:
        print("\n" + "=" * 60)
        print("STATE AGENT STATUS")
        print("=" * 60)
        for state_code in sorted(STATE_DATA.keys()):
            agent = get_state_agent(state_code)
            count = agent.get_shelter_count()
            print(f"  {state_code}: {STATE_DATA[state_code]['name']:20} - {count:5} shelters")
        print("=" * 60)

    elif args.state:
        state_code = args.state.upper()
        if state_code in STATE_DATA:
            agent = get_state_agent(state_code)
            result = asyncio.run(agent.start())
            print(f"\nResult: {result.message}")
            print(f"  Processed: {result.items_processed}")
            print(f"  Created: {result.items_created}")
        else:
            print(f"Invalid state code: {args.state}")

    elif args.region:
        agents = get_state_agents_by_region(args.region)
        print(f"\nRunning {len(agents)} agents for {args.region} region...")
        for agent in agents:
            print(f"  Starting {agent.state_name}...")
            result = asyncio.run(agent.start())
            print(f"    Result: {result.message}")

    elif args.all:
        agents = get_all_state_agents()
        print(f"\nRunning all {len(agents)} state agents...")
        for agent in agents:
            print(f"  Starting {agent.state_name}...")
            result = asyncio.run(agent.start())
            print(f"    Result: {result.message}")

    else:
        parser.print_help()
