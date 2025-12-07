import csv
import sys
import os
import re

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Shelter

def parse_contact_info(contact_str):
    parts = [p.strip() for p in contact_str.split(';')]
    
    email = None
    phone = None
    website = None
    address_parts = []
    
    for part in parts:
        if '@' in part and '.' in part:
            email = part
        elif re.search(r'\d{3}[-.)]', part) or re.search(r'\(\d{3}\)', part):
            phone = part
        elif 'www.' in part or 'http' in part or '.com' in part or '.org' in part:
            website = part
        else:
            address_parts.append(part)
            
    address = ", ".join(address_parts) if address_parts else None
    return address, phone, email, website

def ingest_maryland_rescues():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'maryland_rescues.csv')
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    db = SessionLocal()
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            name = row['Name']
            
            # Check if shelter already exists
            existing = db.query(Shelter).filter(Shelter.name == name).first()
            if existing:
                print(f"Skipping existing shelter: {name}")
                continue
                
            contact_info = row['Contact Info']
            address, phone, email, website = parse_contact_info(contact_info)
            
            description = row['Description']
            # Clean up description (remove contentReference)
            description = re.sub(r':contentReference\[oaicite:\d+\]\{index=\d+\}\.?', '', description)
            
            # Append extra info to description
            extras = []
            if row['Animal Focus']:
                extras.append(f"Focus: {row['Animal Focus']}")
            if row['County']:
                extras.append(f"County: {row['County']}")
            if row['Region']:
                extras.append(f"Region: {row['Region']}")
                
            full_description = description
            if extras:
                full_description += "\n\n" + "\n".join(extras)
            
            shelter = Shelter(
                name=name,
                city=row['City/Town'],
                state=row['State'],
                address=address,
                phone=phone,
                email=email,
                website=website,
                description=full_description,
                source="Maryland Rescue List",
                total_animals=0 # Initialize
            )
            
            db.add(shelter)
            count += 1
            
    db.commit()
    print(f"Successfully ingested {count} Maryland shelters.")

if __name__ == "__main__":
    ingest_maryland_rescues()
