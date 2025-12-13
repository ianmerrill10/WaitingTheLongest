import sys
import os
import re
import logging
from sqlalchemy.orm import Session

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_contact_info(text):
    """Extracts phone and email from text."""
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    phones = re.findall(phone_pattern, text)
    emails = re.findall(email_pattern, text)
    
    phone = phones[0] if phones else None
    email = emails[0] if emails else None
    
    return phone, email

def ingest_akc_network_v2():
    db = SessionLocal()
    count = 0
    
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'akc_rescue_network.txt')
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_breed = None
    table_headers = None
    in_table = False

    for line in lines:
        line = line.strip()
        
        # Detect Breed Headers (heuristic: single line, no punctuation at end, maybe bolded in markdown but here plain text)
        # Actually, looking at the file, breeds are often followed by "Rescue Context:"
        # But we can just parse the lines that look like organizations.
        
        # Table Row Detection
        if line.startswith('|'):
            if 'Organization' in line or 'Department' in line:
                # Header row
                parts = [p.strip() for p in line.split('|') if p.strip()]
                table_headers = [p.lower() for p in parts]
                in_table = True
                continue
            elif '---' in line:
                continue
            else:
                # Data row
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 2:
                    # Map parts to headers if possible, else assume order: Org, Region, Contact...
                    name = parts[0]
                    # Skip if it's a header repetition or empty
                    if name.lower() == 'organization': continue
                    
                    contact_text = " ".join(parts[1:])
                    phone, email = parse_contact_info(contact_text)
                    
                    # Region extraction (heuristic)
                    region = None
                    if len(parts) > 1 and len(parts[1]) < 20: # Short string likely region
                        region = parts[1]
                    
                    # Create Shelter
                    external_id = f"AKC_V2_{count + 1}"
                    
                    # Check duplicate
                    existing = db.query(models.Shelter).filter(
                        models.Shelter.name == name,
                        models.Shelter.source.in_(['akc_rescue_network', 'akc_rescue_network_v2'])
                    ).first()
                    
                    if not existing:
                        shelter = models.Shelter(
                            name=name,
                            source='akc_rescue_network_v2',
                            external_id=external_id,
                            phone=phone,
                            email=email,
                            address=region, # Store region in address for now
                            description=f"Imported from AKC Network Table. Context: {contact_text}"
                        )
                        db.add(shelter)
                        count += 1
                continue

        # Bullet Point Detection
        if line.startswith('* '):
            content = line[2:].strip()
            # Format: * Organization Name: Contact Info
            if ':' in content:
                parts = content.split(':', 1)
                name = parts[0].strip()
                contact_text = parts[1].strip()
                
                # Skip if it looks like a context line ("* Rescue Context: ...")
                if name.lower() == 'rescue context':
                    continue
                
                phone, email = parse_contact_info(contact_text)
                
                external_id = f"AKC_V2_{count + 1}"
                
                existing = db.query(models.Shelter).filter(
                    models.Shelter.name == name,
                    models.Shelter.source.in_(['akc_rescue_network', 'akc_rescue_network_v2'])
                ).first()
                
                if not existing:
                    shelter = models.Shelter(
                        name=name,
                        source='akc_rescue_network_v2',
                        external_id=external_id,
                        phone=phone,
                        email=email,
                        description=f"Imported from AKC Network List. Context: {contact_text}"
                    )
                    db.add(shelter)
                    count += 1
            else:
                # Format: * Organization Name (no colon, maybe contact in parens or next line)
                # Heuristic: if it has a phone number or email, treat as org
                phone, email = parse_contact_info(content)
                if phone or email:
                    name = content.split('(')[0].strip() if '(' in content else content
                    # Clean up name
                    if ',' in name: name = name.split(',')[0].strip()
                    
                    external_id = f"AKC_V2_{count + 1}"
                    
                    existing = db.query(models.Shelter).filter(
                        models.Shelter.name == name,
                        models.Shelter.source.in_(['akc_rescue_network', 'akc_rescue_network_v2'])
                    ).first()
                    
                    if not existing:
                        shelter = models.Shelter(
                            name=name,
                            source='akc_rescue_network_v2',
                            external_id=external_id,
                            phone=phone,
                            email=email,
                            description=f"Imported from AKC Network List (inferred). Context: {content}"
                        )
                        db.add(shelter)
                        count += 1

    db.commit()
    logger.info(f"Ingested {count} new records from AKC Rescue Network V2.")

if __name__ == "__main__":
    ingest_akc_network_v2()
