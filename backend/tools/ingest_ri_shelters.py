import sys
import os
import re
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, init_db
from app.models import Shelter

def parse_contact(contact_str):
    """Extract email, website, phone from contact string."""
    email = None
    website = None
    phone = None
    
    if not contact_str or contact_str == "N/A":
        return email, website, phone

    # Phone extraction
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', contact_str)
    if phone_match:
        phone = phone_match.group(0)

    # Simple email extraction
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_str)
    if email_match:
        email = email_match.group(0)
        
    # Simple website extraction
    website_match = re.search(r'(https?://)?(www\.)?[\w\.-]+\.\w+(/\S*)?', contact_str)
    if website_match:
        # Avoid matching email domain as website
        if not email_match or (email_match and website_match.group(0) not in email_match.group(0)):
             website = website_match.group(0)
         
    return email, website, phone

def ingest_ri_shelters(file_path):
    # Initialize DB tables
    init_db()
    
    db = SessionLocal()
    try:
        print(f"Reading from: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        shelters_to_add = []
        
        # Skip header lines until we find the table start
        start_processing = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "Organization Name" in line and "Type" in line and "Location" in line:
                start_processing = True
                continue
            
            if "7. Conclusion" in line:
                break
            
            if not start_processing:
                continue

            # Split by tab
            parts = line.split('\t')
            if len(parts) < 2:
                # Try splitting by multiple spaces if tabs fail
                parts = re.split(r'\s{2,}', line)
            
            if len(parts) >= 3:
                name = parts[0].strip()
                type_info = parts[1].strip()
                location_raw = parts[2].strip()
                
                contact_raw = ""
                desc = ""
                
                if len(parts) >= 4:
                    contact_raw = parts[3].strip()
                if len(parts) >= 5:
                    desc = parts[4].strip()
                
                # Parse Location
                # e.g. "Warwick (HQ) / Riverside (Clinic)" or "Middletown"
                city = location_raw.split('(')[0].strip() if '(' in location_raw else location_raw
                if '/' in city:
                    city = city.split('/')[0].strip()
                
                state = "RI"
                
                # Parse Contact
                email, website, phone = parse_contact(contact_raw)
                
                # Combine Type into description if useful
                full_desc = f"[{type_info}] {desc}" if desc else f"[{type_info}]"
                
                shelter_data = {
                    "name": name,
                    "description": full_desc,
                    "city": city,
                    "state": state,
                    "email": email,
                    "website": website,
                    "phone": phone,
                    "source": "ri_welfare_report"
                }
                shelters_to_add.append(shelter_data)

        print(f"Found {len(shelters_to_add)} RI shelters to ingest.")
        
        # Database insertion
        count = 0
        updated = 0
        for s_data in shelters_to_add:
            # Check for duplicates by name and state
            query = db.query(Shelter).filter(Shelter.name == s_data["name"])
            if s_data["state"]:
                query = query.filter(Shelter.state == s_data["state"])
            
            existing = query.first()
            
            if existing:
                # Update
                existing.description = s_data["description"]
                if s_data["email"]: existing.email = s_data["email"]
                if s_data["website"]: existing.website = s_data["website"]
                if s_data["phone"]: existing.phone = s_data["phone"]
                if s_data["city"]: existing.city = s_data["city"]
                existing.last_verified_at = datetime.utcnow()
                updated += 1
            else:
                # Create
                new_shelter = Shelter(
                    name=s_data["name"],
                    description=s_data["description"],
                    city=s_data["city"],
                    state=s_data["state"],
                    email=s_data["email"],
                    website=s_data["website"],
                    phone=s_data["phone"],
                    source="ri_welfare_report",
                    last_verified_at=datetime.utcnow()
                )
                db.add(new_shelter)
                count += 1
            
            if (count + updated) % 50 == 0:
                db.commit()
        
        db.commit()
        print(f"Finished! Created: {count}, Updated: {updated}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    default_file = os.path.join(os.path.dirname(__file__), '../data/ri_animal_welfare_report.txt')
    ingest_ri_shelters(default_file)
