import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Animal, Observation, Shelter
from tools.contact_extractor import ContactExtractor
from datetime import datetime

def populate_shelter_info():
    db = SessionLocal()
    try:
        # Get all observations
        observations = db.query(Observation).all()
        print(f"Processing {len(observations)} observations...")
        
        shelters_updated = 0
        
        for obs in observations:
            if not obs.description:
                continue
                
            # Extract info
            info = ContactExtractor.extract(obs.description)
            # print(f"Extracted for {obs.name}: {info}") # Debug
            
            if not any(info.values()):
                continue

            # Find or create shelter
            shelter = None
            if obs.shelter_id:
                shelter = db.query(Shelter).filter(Shelter.id == obs.shelter_id).first()
            
            if not shelter:
                # Try to find by name if we have a real name
                if obs.shelter_name and obs.shelter_name != "Unknown Shelter":
                    shelter = db.query(Shelter).filter(Shelter.name == obs.shelter_name).first()
                
                # If still no shelter, but we have contact info, create one
                if not shelter:
                    # Determine a name
                    name = obs.shelter_name
                    if name == "Unknown Shelter":
                        if info['website']:
                            # Use domain as name
                            from urllib.parse import urlparse
                            try:
                                domain = urlparse(info['website']).netloc
                                name = f"Rescue at {domain}"
                            except:
                                pass
                        elif info['email']:
                            name = f"Rescue at {info['email'].split('@')[-1]}"
                    
                    # Check if we already created this inferred shelter
                    shelter = db.query(Shelter).filter(Shelter.name == name).first()
                    
                    if not shelter:
                        shelter = Shelter(
                            name=name,
                            city=obs.city,
                            state=obs.state,
                            source="inferred"
                        )
                        db.add(shelter)
                        db.flush()
                        print(f"Created new shelter: {shelter.name}")

            if shelter:
                updated = False
                if info['email'] and not shelter.email:
                    shelter.email = info['email']
                    updated = True
                if info['phone'] and not shelter.phone:
                    shelter.phone = info['phone']
                    updated = True
                if info['website'] and not shelter.website:
                    shelter.website = info['website']
                    updated = True
                
                # If we found info, mark verified
                if updated or (info['email'] or info['phone'] or info['website']):
                    shelter.last_verified_at = datetime.utcnow()
                    shelters_updated += 1
                    
                # Link observation if not linked
                if not obs.shelter_id:
                    obs.shelter_id = shelter.id
        
        db.commit()
        print(f"Updated info for {shelters_updated} shelters.")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_shelter_info()
