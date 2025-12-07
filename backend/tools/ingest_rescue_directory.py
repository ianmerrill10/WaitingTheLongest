import sys
import os
import logging
from sqlalchemy.orm import Session

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models
from app.data.rescue_directory import RESCUE_DIRECTORY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_directory():
    db = SessionLocal()
    count = 0
    try:
        # Ingest States
        states = RESCUE_DIRECTORY.get('states', {})
        for state, shelters in states.items():
            for shelter_data in shelters:
                name = shelter_data.get('name')
                
                # Check if exists
                existing = db.query(models.Shelter).filter(
                    models.Shelter.name == name,
                    models.Shelter.source == 'rescue_directory'
                ).first()
                
                if not existing:
                    location = shelter_data.get('location', '')
                    city = None
                    state_code = None
                    if ',' in location:
                        parts = location.split(',')
                        city = parts[0].strip()
                        state_code = parts[1].strip()
                    
                    shelter = models.Shelter(
                        name=name,
                        address=location,
                        city=city,
                        state=state_code,
                        phone=shelter_data.get('phone'),
                        email=shelter_data.get('email'),
                        website=shelter_data.get('website'),
                        description=shelter_data.get('description'),
                        source='rescue_directory',
                        external_id=f"RD_{count + 1}"
                    )
                    db.add(shelter)
                    count += 1

        # Ingest National
        national = RESCUE_DIRECTORY.get('national', {})
        for region, shelters in national.items():
            for shelter_data in shelters:
                name = shelter_data.get('name')
                
                # Check if exists
                existing = db.query(models.Shelter).filter(
                    models.Shelter.name == name,
                    models.Shelter.source == 'rescue_directory'
                ).first()
                
                if not existing:
                    location = shelter_data.get('region', '')
                    city = None
                    state_code = None
                    if ',' in location:
                        parts = location.split(',')
                        city = parts[0].strip()
                        state_code = parts[1].strip()
                    
                    shelter = models.Shelter(
                        name=name,
                        address=location,
                        city=city,
                        state=state_code,
                        phone=shelter_data.get('contact') if 'contact' in shelter_data and any(c.isdigit() for c in shelter_data['contact']) else None, # Heuristic
                        website=shelter_data.get('website'),
                        description=shelter_data.get('description'),
                        source='rescue_directory',
                        external_id=f"RD_NAT_{count + 1}"
                    )
                    db.add(shelter)
                    count += 1

        # Ingest AKC Network from Directory
        akc_network = RESCUE_DIRECTORY.get('akc_network', [])
        for breed_data in akc_network:
            breed = breed_data.get('breed')
            context = breed_data.get('context')
            for contact in breed_data.get('contacts', []):
                name = contact.get('name') or contact.get('organization')
                
                # Check if exists (avoid duplicates with previous AKC ingestion if possible, but source is different)
                # We'll use 'rescue_directory_akc' as source to distinguish
                existing = db.query(models.Shelter).filter(
                    models.Shelter.name == name,
                    models.Shelter.source == 'rescue_directory_akc'
                ).first()
                
                if not existing:
                    shelter = models.Shelter(
                        name=name,
                        description=f"Breed: {breed}. Context: {context}. Source: Rescue Directory.",
                        phone=contact.get('phone'),
                        email=contact.get('email'),
                        website=contact.get('website'),
                        source='rescue_directory_akc',
                        external_id=f"RD_AKC_{count + 1}"
                    )
                    db.add(shelter)
                    count += 1
        
        db.commit()
        logger.info(f"Ingested {count} records from Rescue Directory.")
    except Exception as e:
        logger.error(f"Error ingesting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    ingest_directory()
