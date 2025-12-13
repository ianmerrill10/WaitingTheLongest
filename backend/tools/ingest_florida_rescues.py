import sys
import os
import csv
import re

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Shelter

def create_shelter(db, shelter_data):
    db_shelter = Shelter(**shelter_data)
    db.add(db_shelter)
    db.commit()
    db.refresh(db_shelter)
    return db_shelter

def parse_contact_info(contact_str):
    """
    Extracts email and phone number from a string.
    Examples:
    - "(321) 636-3343 x201"
    - "svprhs@gmail.com"
    - "(954) 530-1508 or (954) 530-1425"
    - "fuzzyrescues@aol.com or (954) 444-5370"
    """
    email = None
    phone = None
    
    # Extract email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_str)
    if email_match:
        email = email_match.group(0)
        
    # Extract phone (first one found)
    # Matches formats like (123) 456-7890, 123-456-7890
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', contact_str)
    if phone_match:
        phone = phone_match.group(0)
        
    return email, phone

def parse_location(location_str):
    """
    Parses "City, FL" into city and state.
    """
    parts = location_str.split(',')
    city = parts[0].strip()
    state = "FL"
    if len(parts) > 1:
        state_part = parts[1].strip()
        if len(state_part) == 2:
            state = state_part
            
    return city, state

def ingest_florida_rescues():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'florida_rescues.csv')
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    db = SessionLocal()
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            name = row['Name'].strip()
            location = row['Location'].strip()
            contact_info = row['Contact Information'].strip()
            description = row['Description'].strip()
            
            city, state = parse_location(location)
            email, phone = parse_contact_info(contact_info)
            
            shelter_data = {
                "name": name,
                "city": city,
                "state": state,
                "email": email,
                "phone": phone,
                "description": description,
                "source": "Florida Rescues List"
            }
            
            try:
                create_shelter(db, shelter_data)
                count += 1
            except Exception as e:
                print(f"Error creating shelter {name}: {e}")
                db.rollback()

    db.close()
    print(f"Successfully ingested {count} Florida rescues.")

if __name__ == "__main__":
    ingest_florida_rescues()
