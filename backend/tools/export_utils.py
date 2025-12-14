"""
Waiting The Longest™ - Export Utilities
=======================================
Export animal data in various formats for sharing and analytics.
"""

import csv
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional, TextIO
from io import StringIO, BytesIO
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session


@dataclass
class AnimalExport:
    """Represents exported animal data."""
    id: int
    name: str
    species: str
    breed: str
    age: str
    gender: str
    days_waiting: int
    intake_date: str
    shelter_name: str
    shelter_city: str
    shelter_state: str
    photo_url: str
    description: str


class DataExporter:
    """
    Export animal and shelter data in various formats.
    
    Supports:
    - CSV for spreadsheets
    - JSON for APIs
    - Markdown for documentation
    - HTML for email newsletters
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_animals_data(
        self,
        species: Optional[str] = None,
        min_days_waiting: Optional[int] = None,
        shelter_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AnimalExport]:
        """Fetch animals and convert to export format."""
        from app.models import Animal, Shelter
        
        query = self.db.query(Animal, Shelter).join(
            Shelter, Animal.shelter_id == Shelter.id
        )
        
        if species:
            query = query.filter(Animal.species.ilike(species))
        
        if min_days_waiting:
            min_date = date.today() - timedelta(days=min_days_waiting)
            query = query.filter(Animal.intake_date <= min_date)
        
        if shelter_id:
            query = query.filter(Animal.shelter_id == shelter_id)
        
        query = query.order_by(Animal.intake_date.asc())
        
        if limit:
            query = query.limit(limit)
        
        results = []
        for animal, shelter in query.all():
            days = (date.today() - animal.intake_date).days if animal.intake_date else 0
            results.append(AnimalExport(
                id=animal.id,
                name=animal.name,
                species=animal.species or "",
                breed=animal.breed or "",
                age=animal.age or "",
                gender=animal.gender or "",
                days_waiting=days,
                intake_date=animal.intake_date.isoformat() if animal.intake_date else "",
                shelter_name=shelter.name or "",
                shelter_city=shelter.city or "",
                shelter_state=shelter.state or "",
                photo_url=animal.photo_url or "",
                description=animal.description or "",
            ))
        
        return results
    
    def export_csv(
        self,
        output: Optional[TextIO] = None,
        **filters,
    ) -> str:
        """Export animals to CSV format."""
        animals = self._get_animals_data(**filters)
        
        if output is None:
            output = StringIO()
        
        if not animals:
            return ""
        
        fieldnames = list(asdict(animals[0]).keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for animal in animals:
            writer.writerow(asdict(animal))
        
        if isinstance(output, StringIO):
            return output.getvalue()
        return ""
    
    def export_json(
        self,
        pretty: bool = False,
        **filters,
    ) -> str:
        """Export animals to JSON format."""
        animals = self._get_animals_data(**filters)
        
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "count": len(animals),
            "animals": [asdict(a) for a in animals],
        }
        
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)
    
    def export_markdown(
        self,
        title: str = "Animals Waiting for Adoption",
        **filters,
    ) -> str:
        """Export animals to Markdown format."""
        animals = self._get_animals_data(**filters)
        
        lines = [
            f"# {title}",
            f"",
            f"*Generated on {datetime.utcnow().strftime('%B %d, %Y')}*",
            f"",
            f"**Total Animals: {len(animals)}**",
            f"",
            "| Name | Species | Breed | Days Waiting | Shelter | Location |",
            "|------|---------|-------|--------------|---------|----------|",
        ]
        
        for animal in animals[:50]:  # Limit for readability
            lines.append(
                f"| {animal.name} | {animal.species} | {animal.breed} | "
                f"{animal.days_waiting} | {animal.shelter_name} | "
                f"{animal.shelter_city}, {animal.shelter_state} |"
            )
        
        if len(animals) > 50:
            lines.append(f"")
            lines.append(f"*... and {len(animals) - 50} more animals*")
        
        return "\n".join(lines)
    
    def export_html_newsletter(
        self,
        title: str = "Meet Our Longest Residents",
        limit: int = 5,
        **filters,
    ) -> str:
        """Export animals as HTML for email newsletters."""
        filters["limit"] = limit
        animals = self._get_animals_data(**filters)
        
        html_parts = [
            f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 20px; }}
        .animal-card {{ border: 1px solid #eee; border-radius: 8px; margin: 15px 0; overflow: hidden; }}
        .animal-image {{ width: 100%; height: 200px; object-fit: cover; }}
        .animal-info {{ padding: 15px; }}
        .animal-name {{ font-size: 18px; font-weight: bold; color: #333; margin: 0 0 5px 0; }}
        .animal-meta {{ color: #666; font-size: 14px; }}
        .days-badge {{ display: inline-block; background: #ff6b6b; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .cta-button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px; }}
        .footer {{ background: #f9f9f9; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐾 {title}</h1>
            <p>These wonderful animals have been waiting the longest for their forever homes</p>
        </div>
        <div class="content">
""",
        ]
        
        for animal in animals:
            photo = animal.photo_url or "https://placedog.net/400/300"
            html_parts.append(f"""
            <div class="animal-card">
                <img src="{photo}" alt="{animal.name}" class="animal-image">
                <div class="animal-info">
                    <h3 class="animal-name">{animal.name}</h3>
                    <p class="animal-meta">
                        {animal.breed} • {animal.age} • {animal.gender}<br>
                        📍 {animal.shelter_name}, {animal.shelter_city}, {animal.shelter_state}
                    </p>
                    <span class="days-badge">Waiting {animal.days_waiting} days</span>
                    <br>
                    <a href="https://waitingthelongest.com/animal/{animal.id}" class="cta-button">
                        Meet {animal.name}
                    </a>
                </div>
            </div>
""")
        
        html_parts.append("""
        </div>
        <div class="footer">
            <p>Thank you for caring about shelter animals! 💜</p>
            <p>Waiting The Longest™ - Helping long-term shelter animals find homes</p>
        </div>
    </div>
</body>
</html>
""")
        
        return "".join(html_parts)
    
    def export_social_post(
        self,
        platform: str = "twitter",
        animal_id: Optional[int] = None,
        **filters,
    ) -> str:
        """Generate social media post text for an animal."""
        if animal_id:
            from app.models import Animal, Shelter
            animal = self.db.query(Animal).filter(Animal.id == animal_id).first()
            if not animal:
                return ""
            shelter = self.db.query(Shelter).filter(Shelter.id == animal.shelter_id).first()
            animals = [AnimalExport(
                id=animal.id,
                name=animal.name,
                species=animal.species or "",
                breed=animal.breed or "",
                age=animal.age or "",
                gender=animal.gender or "",
                days_waiting=(date.today() - animal.intake_date).days if animal.intake_date else 0,
                intake_date=animal.intake_date.isoformat() if animal.intake_date else "",
                shelter_name=shelter.name if shelter else "",
                shelter_city=shelter.city if shelter else "",
                shelter_state=shelter.state if shelter else "",
                photo_url=animal.photo_url or "",
                description=animal.description or "",
            )]
        else:
            filters["limit"] = 1
            animals = self._get_animals_data(**filters)
        
        if not animals:
            return ""
        
        animal = animals[0]
        
        if platform.lower() in ("twitter", "x"):
            # Twitter: 280 character limit
            return (
                f"🐾 Meet {animal.name}! This {animal.breed.lower()} has been waiting "
                f"{animal.days_waiting} days for a forever home at {animal.shelter_name}. "
                f"Could you be their perfect match? 💜\n\n"
                f"#AdoptDontShop #ShelterPets #WaitingTheLongest"
            )[:280]
        
        elif platform.lower() == "instagram":
            # Instagram: Longer format
            return (
                f"🐾 Meet {animal.name}!\n\n"
                f"This beautiful {animal.breed.lower()} has been patiently waiting "
                f"at {animal.shelter_name} in {animal.shelter_city}, {animal.shelter_state} "
                f"for {animal.days_waiting} days.\n\n"
                f"Could YOU give {animal.name} the forever home they deserve? 💜\n\n"
                f"📍 {animal.shelter_city}, {animal.shelter_state}\n\n"
                f"#AdoptDontShop #ShelterPets #ShelterDogsOfInstagram #RescueDog "
                f"#AdoptAShelterPet #WaitingTheLongest #ShelterPetsAreFamily"
            )
        
        elif platform.lower() == "facebook":
            # Facebook: Full description
            return (
                f"🐾 FEATURED: {animal.name} - Waiting {animal.days_waiting} Days\n\n"
                f"{animal.name} is a {animal.age.lower()} {animal.gender.lower()} "
                f"{animal.breed} who has been waiting patiently at {animal.shelter_name} "
                f"in {animal.shelter_city}, {animal.shelter_state}.\n\n"
                f"{animal.description[:200]}...\n\n"
                f"Could you be the one to give {animal.name} their happy ending? "
                f"Share this post to help them find their forever home! 💜\n\n"
                f"🔗 Learn more at WaitingTheLongest.com"
            )
        
        elif platform.lower() == "tiktok":
            # TikTok: Short, engaging
            return (
                f"This is {animal.name}.\n"
                f"They've been waiting {animal.days_waiting} days for someone to love them.\n"
                f"Will it be you? 🥺💜\n\n"
                f"#fyp #adoptdontshop #shelterpet #waitingthelongest"
            )
        
        return f"{animal.name} - {animal.breed} - Waiting {animal.days_waiting} days"


from datetime import timedelta  # Import needed for _get_animals_data
