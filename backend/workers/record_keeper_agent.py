"""
===============================================================================
RecordKeeper Agent
===============================================================================
Purpose: Automated agent to ingest and maintain a master list of animal shelters
         and rescue organizations across all 50 states.
         
         Currently supports:
         - Mass.gov Approved Shelter and Rescue Organizations

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import logging
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Shelter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RecordKeeper")

class RecordKeeperAgent:
    def __init__(self):
        self.db = SessionLocal()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }

    def run(self):
        """Main execution method"""
        logger.info("RecordKeeper Agent starting...")
        
        # Ingest from Mass.gov
        self.ingest_mass_gov()
        
        # Future: Add other state sources here
        
        logger.info("RecordKeeper Agent finished.")

    def ingest_mass_gov(self):
        """Ingest data from Mass.gov approved shelters list"""
        url = "https://www.mass.gov/info-details/approved-shelter-and-rescue-organizations"
        logger.info(f"Ingesting data from {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all tables
            tables = soup.find_all('table')
            total_processed = 0
            
            for table in tables:
                rows = table.find_all('tr')
                if not rows:
                    continue
                    
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    # We expect at least 5 columns based on the page structure
                    # ID | Name | State | Type | Email
                    if len(cols) < 5:
                        continue
                        
                    col_texts = [c.get_text(strip=True) for c in cols]
                    
                    # Skip header rows
                    if "Organization" in col_texts[1] or "Name" in col_texts[1]:
                        continue
                        
                    # Extract data
                    # Note: The first column is often an ID number
                    try:
                        external_id = col_texts[0]
                        name = col_texts[1]
                        state = col_texts[2]
                        license_type = col_texts[3]
                        email = col_texts[4]
                        
                        # Basic validation
                        if not name or len(name) < 2:
                            continue
                            
                        # Clean up email (sometimes has extra spaces or hidden chars)
                        email = email.strip() if email else None
                        
                        self.upsert_shelter(
                            name=name,
                            state=state,
                            email=email,
                            source="mass.gov",
                            external_id=external_id,
                            description=f"MA License Type: {license_type}"
                        )
                        total_processed += 1
                        
                    except IndexError:
                        continue
                        
            logger.info(f"Successfully processed {total_processed} records from Mass.gov")

        except Exception as e:
            logger.error(f"Error ingesting Mass.gov data: {e}")

    def upsert_shelter(self, name, state, email, source, external_id=None, description=None):
        """Insert or Update a shelter record"""
        try:
            # Try to find existing shelter by email (most reliable unique identifier)
            existing = None
            if email and "@" in email:
                existing = self.db.query(Shelter).filter(Shelter.email == email).first()
            
            # If not found by email, try by name and state
            if not existing and name:
                existing = self.db.query(Shelter).filter(
                    Shelter.name == name,
                    Shelter.state == state
                ).first()
                
            if existing:
                # Update existing record
                existing.source = source
                existing.last_verified_at = datetime.utcnow()
                
                # Only update fields if they are missing or we have better data
                if not existing.external_id and external_id:
                    existing.external_id = external_id
                
                if not existing.description and description:
                    existing.description = description
                elif description and description not in (existing.description or ""):
                    existing.description = (existing.description or "") + f"\n{description}"
                    
                # logger.info(f"Updated shelter: {name}")
            else:
                # Create new record
                new_shelter = Shelter(
                    name=name,
                    state=state,
                    email=email,
                    source=source,
                    external_id=external_id,
                    description=description,
                    last_verified_at=datetime.utcnow(),
                    total_animals=0 # Initialize
                )
                self.db.add(new_shelter)
                logger.info(f"Created new shelter: {name} ({state})")
                
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error processing {name}: {e}")

if __name__ == "__main__":
    agent = RecordKeeperAgent()
    agent.run()
