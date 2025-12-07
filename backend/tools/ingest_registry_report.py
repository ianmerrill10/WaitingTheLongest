import sys
import os
import re
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, init_db
from app.models import Shelter

def clean_str(s):
    if not s:
        return None
    return s.strip()

def parse_contact(contact_str):
    """Extract email and website from contact string."""
    email = None
    website = None
    phone = None
    
    if not contact_str or contact_str == "N/A":
        return email, website, phone

    # Simple email extraction
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_str)
    if email_match:
        email = email_match.group(0)
        
    # Simple website extraction
    website_match = re.search(r'(https?://)?(www\.)?[\w\.-]+\.\w+(/\S*)?', contact_str)
    if website_match and not email_match: # Avoid matching email domain as website
         website = website_match.group(0)
    elif website_match and email_match and website_match.group(0) not in email:
         website = website_match.group(0)
         
    return email, website, phone

def ingest_report(file_path):
    # Initialize DB tables
    init_db()
    
    db = SessionLocal()
    try:
        print(f"Reading from: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_section = None
        current_state = None
        headers = []
        
        shelters_to_add = []
        current_shelter = None # {name, ...}

        # Regex for section headers like "3.1 Massachusetts"
        section_re = re.compile(r'^\d+\.\d+\s+(.*)')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for section header
            section_match = section_re.match(line)
            if section_match:
                current_section = section_match.group(1)
                print(f"Processing Section: {current_section}")
                
                # Infer state from section
                if "Massachusetts" in current_section: current_state = "MA"
                elif "New York" in current_section: current_state = "NY"
                elif "Pennsylvania" in current_section: current_state = "PA"
                elif "Texas" in current_section: current_state = "TX"
                elif "Florida" in current_section: current_state = "FL"
                elif "Virginia" in current_section: current_state = "VA"
                elif "Ohio" in current_section: current_state = "OH"
                elif "California" in current_section: current_state = "CA"
                else: current_state = None # Reset if mixed region
                
                headers = [] # Reset headers
                continue

            # Check for table headers
            if "Organization Name" in line or "Organization" in line:
                # Split by tab or multiple spaces
                parts = re.split(r'\t+', line)
                if len(parts) < 2:
                     parts = re.split(r'\s{2,}', line)
                headers = [h.strip() for h in parts]
                print(f"  Found headers: {headers}")
                continue

            # If we have headers, try to parse row
            if headers:
                parts = re.split(r'\t+', line)
                # If not tab separated, try 2+ spaces
                if len(parts) < 2:
                     parts = re.split(r'\s{2,}', line)
                
                # If it looks like a new row (has multiple parts)
                if len(parts) >= 2:
                    # Save previous shelter if exists
                    if current_shelter:
                        shelters_to_add.append(current_shelter)
                        current_shelter = None

                    # Parse new row based on headers
                    data = {}
                    # Map parts to headers by index
                    for i, h in enumerate(headers):
                        if i < len(parts):
                            data[h] = parts[i].strip()
                    
                    # Extract fields
                    name = data.get("Organization Name") or data.get("Organization")
                    if not name: continue

                    desc = data.get("Description") or data.get("Operational Description")
                    
                    # Handle "Scope" for breed rescues
                    if data.get("Scope"):
                        scope = data.get("Scope")
                        if desc:
                            desc = f"{scope} - {desc}"
                        else:
                            desc = scope

                    # Location/City/State logic
                    city = data.get("City") or data.get("Location") or data.get("City/Region") or data.get("County/City")
                    state = current_state
                    
                    # Handle "Location" field which might be "MA (Statewide)" or "Boston"
                    if city and "Statewide" in city:
                        city = None # It's statewide
                    
                    # Handle "State" column if exists (AZ/PNW section)
                    if data.get("State"):
                        state_val = data.get("State")
                        # Extract state code if like "AZ (Phoenix)"
                        if "(" in state_val:
                            state = state_val.split("(")[0].strip()
                        else:
                            state = state_val

                    # Handle "Location" in IL/MI section which might be "Chicago, IL"
                    if data.get("Location") and "," in data.get("Location"):
                        loc_parts = data.get("Location").split(",")
                        city = loc_parts[0].strip()
                        state = loc_parts[1].strip()

                    # Contact info
                    contact_raw = data.get("Contact / Email") or data.get("Contact") or data.get("Contact / Website") or data.get("Contact/Notes")
                    email, website, phone = parse_contact(contact_raw)
                    
                    # If we have notes in contact (common in breed section), append to description
                    if data.get("Contact/Notes") and contact_raw:
                        # Remove email/website from contact_raw to get notes
                        notes = contact_raw
                        if email: notes = notes.replace(email, "")
                        if website: notes = notes.replace(website, "")
                        notes = notes.strip(" ;,\t\n")
                        if notes:
                            if desc:
                                desc += f". {notes}"
                            else:
                                desc = notes
                    
                    # External ID
                    ext_id = data.get("Reg ID") or data.get("License Type") # Use license type as ID if unique? No.
                    if data.get("Reg ID"):
                        ext_id = data.get("Reg ID")
                    else:
                        ext_id = None

                    current_shelter = {
                        "name": name,
                        "description": desc,
                        "city": city,
                        "state": state,
                        "email": email,
                        "website": website,
                        "phone": phone,
                        "external_id": ext_id,
                        "source": "national_registry_report"
                    }
                
                else:
                    # Continuation line?
                    if current_shelter and len(parts) == 1:
                        # Append to description
                        if current_shelter["description"]:
                            current_shelter["description"] += " " + parts[0].strip()
                        else:
                            current_shelter["description"] = parts[0].strip()

        # Add last shelter
        if current_shelter:
            shelters_to_add.append(current_shelter)

        print(f"Found {len(shelters_to_add)} shelters to ingest.")
        
        # Database insertion
        count = 0
        updated = 0
        for s_data in shelters_to_add:
            # Check for duplicates by name and state (since external_id is rare here)
            query = db.query(Shelter).filter(Shelter.name == s_data["name"])
            if s_data["state"]:
                query = query.filter(Shelter.state == s_data["state"])
            
            existing = query.first()
            
            if existing:
                # Update
                existing.description = s_data["description"]
                if s_data["email"]: existing.email = s_data["email"]
                if s_data["website"]: existing.website = s_data["website"]
                if s_data["city"]: existing.city = s_data["city"]
                if s_data["external_id"]: existing.external_id = s_data["external_id"]
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
                    external_id=s_data["external_id"],
                    source="national_registry_report",
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
    default_file = os.path.join(os.path.dirname(__file__), '../data/national_registry_report.txt')
    ingest_report(default_file)
