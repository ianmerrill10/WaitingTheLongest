import sys
import os
import re
import logging
from sqlalchemy.orm import Session

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_akc_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by lines
    lines = content.split('\n')
    
    shelters = []
    current_breed = "Unknown"
    
    # Regex patterns
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    # Iterate through lines to find tables and lists
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect breed headers (simple heuristic: single word or short phrase on a line, maybe followed by "Rescue Context")
        if i + 1 < len(lines) and "Rescue Context" in lines[i+1]:
             current_breed = line
             i += 1
             continue

        # Parse Markdown Tables
        if line.startswith('|'):
            # Skip header separator and header row if it contains "Organization"
            if '---' in line or 'Organization' in line:
                i += 1
                continue
            
            # Parse row
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                name = parts[0]
                
                # Find email and phone in the parts
                email = None
                phone = None
                
                for part in parts:
                    emails = re.findall(email_pattern, part)
                    if emails:
                        email = emails[0]
                    
                    phones = re.findall(phone_pattern, part)
                    if phones:
                        phone = phones[0]
                        
                shelters.append({
                    "name": name,
                    "description": f"Breed: {current_breed}. Source: AKC Rescue Network.",
                    "email": email,
                    "phone": phone,
                    "source": "akc_rescue_network",
                    "external_id": f"AKC_{len(shelters) + 1}"
                })
        
        # Parse Bulleted Lists
        elif line.startswith('*'):
            # * Organization Name
            #    * Contact: ...
            
            if not line.startswith('   *'): # Top level bullet
                name = line.strip('* ').split(':')[0].strip() # Handle "Name: Contact" format
                
                # Check for inline contact info
                email = None
                phone = None
                
                emails = re.findall(email_pattern, line)
                if emails:
                    email = emails[0]
                
                phones = re.findall(phone_pattern, line)
                if phones:
                    phone = phones[0]
                
                # Look ahead for nested bullets with details
                j = i + 1
                while j < len(lines) and lines[j].startswith('   *'):
                    subline = lines[j]
                    emails_sub = re.findall(email_pattern, subline)
                    if emails_sub and not email:
                        email = emails_sub[0]
                    
                    phones_sub = re.findall(phone_pattern, subline)
                    if phones_sub and not phone:
                        phone = phones_sub[0]
                    j += 1
                
                shelters.append({
                    "name": name,
                    "description": f"Breed: {current_breed}. Source: AKC Rescue Network.",
                    "email": email,
                    "phone": phone,
                    "source": "akc_rescue_network",
                    "external_id": f"AKC_{len(shelters) + 1}"
                })
        
        i += 1
        
    return shelters

def ingest_data(shelters):
    db = SessionLocal()
    count = 0
    try:
        for shelter_data in shelters:
            # Check if exists
            existing = db.query(models.Shelter).filter(
                models.Shelter.name == shelter_data['name'],
                models.Shelter.source == shelter_data['source']
            ).first()
            
            if not existing:
                shelter = models.Shelter(**shelter_data)
                db.add(shelter)
                count += 1
        
        db.commit()
        logger.info(f"Ingested {count} records from AKC Rescue Network.")
    except Exception as e:
        logger.error(f"Error ingesting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'akc_rescue_network.txt')
    if os.path.exists(file_path):
        data = parse_akc_file(file_path)
        logger.info(f"Parsed {len(data)} records.")
        ingest_data(data)
    else:
        logger.error(f"File not found: {file_path}")
