import sys
import os
import re

# Add the parent directory to sys.path to allow importing app modules
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
    Extracts address and phone number from a string like:
    '1067 NE Columbia Blvd, Portland, OR 97211 (503-285-7722)'
    """
    phone_match = re.search(r'\((\d{3}[-.]?\d{3}[-.]?\d{4})\)', contact_str)
    phone = phone_match.group(1) if phone_match else None
    
    address = contact_str
    if phone_match:
        address = contact_str.replace(phone_match.group(0), '').strip()
    
    return address, phone

def ingest_oregon_rescues():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'oregon_rescues.txt')
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    db = SessionLocal()
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_shelter = None
    
    for line in lines:
        line = line.strip('\n') # Keep leading whitespace for description detection
        
        # Skip empty lines
        if not line.strip():
            continue
            
        # Check for Data Line (Tab separated)
        # The header line also has tabs, so we exclude it specifically
        if '\t' in line and "Name (Shelter/Humane Society)" not in line:
            # If we have a previous shelter pending, save it (though we usually save immediately, 
            # but here we might need to wait for description)
            # Actually, let's save the previous one if we haven't already? 
            # No, let's parse the current line and start a new shelter object.
            
            parts = line.split('\t')
            if len(parts) >= 3:
                name = parts[0].strip()
                location = parts[1].strip()
                contact_raw = parts[2].strip()
                
                address, phone = parse_contact_info(contact_raw)
                
                # Sometimes the description is in the 4th column if it exists
                description = parts[3].strip() if len(parts) > 3 else None
                
                current_shelter = {
                    "name": name,
                    "city": location, # We can use location as city
                    "address": address,
                    "phone": phone,
                    "state": "OR",
                    "description": description,
                    "source": "Oregon Rescues List"
                }
                
                # If description was found in the line, we might be done, but let's see if there's more
                if description:
                    # Create immediately
                    create_shelter(db, current_shelter)
                    count += 1
                    current_shelter = None # Reset
                
            continue

        # If we are inside a shelter entry and looking for description
        if current_shelter:
            stripped = line.strip()
            
            # Skip URL lines
            if re.search(r'\.(com|org|net|gov|edu)', stripped):
                continue
                
            # Skip lines that are just punctuation
            if stripped == '.':
                continue
                
            # If the line starts with a tab or is indented, it's likely the description
            # Or if we haven't found a description yet and this is a text line
            if not current_shelter["description"]:
                current_shelter["description"] = stripped
                
                # Save it now
                create_shelter(db, current_shelter)
                count += 1
                current_shelter = None # Reset
            else:
                # We already have a description, maybe append? 
                # The format seems to have one main description block.
                pass

    db.close()
    print(f"Successfully ingested {count} Oregon rescues.")

if __name__ == "__main__":
    ingest_oregon_rescues()
