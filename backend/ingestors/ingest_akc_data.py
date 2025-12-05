import re
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Shelter
from sqlalchemy.exc import IntegrityError

def parse_and_ingest():
    file_path = os.path.join(os.path.dirname(__file__), "../data/akc_rescue_network.txt")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by lines
    lines = content.split('\n')
    
    db = SessionLocal()
    
    shelters_added = 0
    
    # Regex for email and phone
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    print("Starting ingestion...")

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        name = None
        details = ""
        
        # Check for bullet point organizations
        if line.startswith("*"):
            # * Organization Name: Contact info
            content = line[1:].strip()
            
            # Split by colon if present to separate name from details
            # But be careful, sometimes it's "Name: details"
            # Sometimes it's "Name"
            
            if ":" in content:
                parts = content.split(":", 1)
                name = parts[0].strip()
                details = parts[1].strip()
            else:
                name = content
                details = ""

        # Check for Table Rows
        elif line.startswith("|") and not line.startswith("|---"):
            # | Organization | Contact | ...
            parts = [p.strip() for p in line.split("|") if p.strip()]
            
            if not parts or parts[0] == "Organization" or parts[0] == "Department":
                continue
                
            name = parts[0]
            # Join the rest as details
            details = " ".join(parts[1:])
        
        if name:
            # Clean up name (remove trailing chars if any)
            name = name.strip()
            
            # Extract email and phone from details
            emails = re.findall(email_pattern, details)
            phones = re.findall(phone_pattern, details)
            
            email = emails[0] if emails else None
            phone = phones[0] if phones else None
            
            # If we found a name, try to insert
            # Filter out some noise
            if len(name) > 3 and "Section" not in name and "Rescue Context" not in name:
                create_shelter(db, name, email, phone, details)
                shelters_added += 1

    try:
        db.commit()
        print(f"Successfully processed and committed {shelters_added} shelters.")
    except Exception as e:
        db.rollback()
        print(f"Error committing to database: {e}")
    finally:
        db.close()

def create_shelter(db, name, email, phone, description):
    # Simple deduplication by name
    existing = db.query(Shelter).filter(Shelter.name == name).first()
    if existing:
        # Update if we have new info and old was empty? 
        # For now, just skip to avoid duplicates
        # print(f"Skipping existing: {name}")
        return

    shelter = Shelter(
        name=name,
        source="akc_directory",
        email=email,
        phone=phone,
        description=description,
        total_animals=0 # Initial state
    )
    db.add(shelter)
    print(f"Added: {name}")

if __name__ == "__main__":
    parse_and_ingest()
