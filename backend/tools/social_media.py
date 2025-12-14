"""
Waiting The Longest™ - Social Media Manager
=============================================
Automated social media content generation and scheduling.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class Platform(Enum):
    """Supported social media platforms."""
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    THREADS = "threads"


@dataclass
class SocialPost:
    """A social media post."""
    platform: Platform
    content: str
    hashtags: List[str]
    media_urls: List[str]
    scheduled_for: Optional[datetime] = None
    animal_id: Optional[int] = None
    
    @property
    def full_content(self) -> str:
        """Get content with hashtags."""
        hashtag_str = " ".join(f"#{tag}" for tag in self.hashtags)
        return f"{self.content}\n\n{hashtag_str}"
    
    @property
    def character_count(self) -> int:
        """Get total character count."""
        return len(self.full_content)


class SocialMediaManager:
    """
    Manage social media content creation and scheduling.
    
    Generates platform-specific content for animals.
    """
    
    # Platform-specific constraints
    PLATFORM_LIMITS = {
        Platform.TWITTER: {"chars": 280, "hashtags": 3},
        Platform.FACEBOOK: {"chars": 63206, "hashtags": 5},
        Platform.INSTAGRAM: {"chars": 2200, "hashtags": 30},
        Platform.TIKTOK: {"chars": 2200, "hashtags": 10},
        Platform.THREADS: {"chars": 500, "hashtags": 5},
    }
    
    # Common hashtags for animal rescue
    BASE_HASHTAGS = [
        "AdoptDontShop", "RescueDog", "RescueCat", "ShelterPets",
        "AdoptAShelterPet", "SaveALife", "WaitingForAdoption",
        "ForeverHome", "RescuePets", "ShelterAnimals",
    ]
    
    # Emotional hooks by waiting duration
    WAITING_HOOKS = {
        7: ["still waiting", "needs a home"],
        30: ["overlooked for a month", "a month of waiting"],
        60: ["two months waiting", "still hoping"],
        90: ["three months alone", "90 days too long"],
        180: ["half a year waiting", "6 months of hope"],
        365: ["one year waiting", "a whole year"],
    }
    
    # Call-to-action templates
    CTAS = [
        "Could you be the one? 🏠",
        "Share to help find their person! 💕",
        "Every share helps! 🙏",
        "Will you give them a chance? ❤️",
        "Be their hero today! 🦸",
        "Open your heart and home! 🐾",
    ]
    
    def __init__(self):
        self.scheduled_posts: List[SocialPost] = []
    
    def generate_post(
        self,
        animal: Dict[str, Any],
        platform: Platform,
    ) -> SocialPost:
        """Generate a platform-optimized post for an animal."""
        limits = self.PLATFORM_LIMITS[platform]
        
        # Build the content
        content = self._create_content(animal, platform)
        
        # Select hashtags
        hashtags = self._select_hashtags(animal, platform)
        
        # Get media URLs
        media_urls = []
        if animal.get("photo_url"):
            media_urls.append(animal["photo_url"])
        
        return SocialPost(
            platform=platform,
            content=content,
            hashtags=hashtags[:limits["hashtags"]],
            media_urls=media_urls,
            animal_id=animal.get("id"),
        )
    
    def _create_content(self, animal: Dict[str, Any], platform: Platform) -> str:
        """Create platform-specific content."""
        name = animal.get("name", "This sweetie")
        days = animal.get("days_waiting", 0)
        breed = animal.get("breed", "")
        age = animal.get("age", "")
        
        # Find appropriate hook based on waiting duration
        hook = "waiting for a home"
        for threshold, hooks in sorted(self.WAITING_HOOKS.items()):
            if days >= threshold:
                hook = random.choice(hooks)
        
        # Select a CTA
        cta = random.choice(self.CTAS)
        
        if platform == Platform.TWITTER:
            # Short and punchy for Twitter
            if breed and age:
                content = f"Meet {name}, a {age} {breed} who's been {hook} for {days} days. {cta}"
            else:
                content = f"{name} has been {hook} for {days} days. {cta}"
        
        elif platform == Platform.INSTAGRAM:
            # Longer, more emotional for Instagram
            content = f"""🐾 {name}'s Story 🐾

This beautiful soul has been waiting {days} days for someone to say "you're coming home with me."

{self._get_description(animal)}

📍 {animal.get('shelter_name', 'Local Shelter')}

{cta}

Link in bio to learn more! 🔗"""
        
        elif platform == Platform.TIKTOK:
            # Casual, Gen-Z friendly for TikTok
            content = f"""POV: You just found your new best friend 🥹

{name} has been waiting {days} days at the shelter.

{days} days of hoping someone would choose them.
{days} days of watching other pets go home.
{days} days of waiting...

Be the reason their wait ends today. 🏠💕"""
        
        elif platform == Platform.FACEBOOK:
            # Detailed for Facebook
            content = f"""🐾 ADOPTABLE: {name}

{name} has been at {animal.get('shelter_name', 'the shelter')} for {days} days, patiently waiting for their forever family.

{self._get_description(animal)}

✨ Details:
• Age: {age or 'Ask us!'}
• Breed: {breed or 'Unique mix'}
• Location: {animal.get('shelter_city', '')}, {animal.get('shelter_state', '')}

{cta}

🔗 Visit waitingthelongest.com to meet {name} and other overlooked pets who need your help."""
        
        else:
            # Default/Threads
            content = f"{name}: {days} days waiting. {breed if breed else 'A sweetheart'} looking for their person. {cta}"
        
        return content
    
    def _get_description(self, animal: Dict[str, Any]) -> str:
        """Get a description or generate one."""
        if animal.get("description"):
            # Truncate if too long
            desc = animal["description"]
            if len(desc) > 200:
                desc = desc[:197] + "..."
            return desc
        
        # Generate a generic description
        species = animal.get("species", "pet").lower()
        templates = [
            f"A wonderful {species} with so much love to give!",
            f"This gentle {species} deserves a second chance.",
            f"A loyal companion waiting to steal your heart!",
            f"Sweet and loving - perfect for the right family!",
        ]
        return random.choice(templates)
    
    def _select_hashtags(
        self,
        animal: Dict[str, Any],
        platform: Platform,
    ) -> List[str]:
        """Select relevant hashtags for the post."""
        hashtags = ["WaitingTheLongest"]
        
        # Add species-specific hashtags
        species = animal.get("species", "").lower()
        if species == "dog":
            hashtags.extend(["DogsOfInstagram", "RescueDog", "AdoptADog"])
        elif species == "cat":
            hashtags.extend(["CatsOfInstagram", "RescueCat", "AdoptACat"])
        
        # Add breed hashtag if available
        breed = animal.get("breed", "")
        if breed:
            breed_tag = breed.replace(" ", "")
            hashtags.append(breed_tag)
        
        # Add state hashtag
        state = animal.get("state", "")
        if state:
            hashtags.append(f"{state}Rescue")
        
        # Add base hashtags
        hashtags.extend(random.sample(self.BASE_HASHTAGS, min(3, len(self.BASE_HASHTAGS))))
        
        return hashtags
    
    def generate_weekly_content(
        self,
        animals: List[Dict[str, Any]],
        platforms: Optional[List[Platform]] = None,
    ) -> List[SocialPost]:
        """Generate a week's worth of social content."""
        if platforms is None:
            platforms = [Platform.TWITTER, Platform.INSTAGRAM, Platform.FACEBOOK]
        
        posts = []
        
        # Generate posts for top waiting animals
        for i, animal in enumerate(animals[:7]):  # One per day
            scheduled_date = datetime.utcnow() + timedelta(days=i)
            
            for platform in platforms:
                post = self.generate_post(animal, platform)
                post.scheduled_for = scheduled_date
                posts.append(post)
        
        return posts
    
    def export_content_calendar(
        self,
        posts: List[SocialPost],
    ) -> str:
        """Export posts as a content calendar (CSV format)."""
        lines = ["Date,Platform,Content,Hashtags,Media"]
        
        for post in posts:
            date = post.scheduled_for.strftime("%Y-%m-%d") if post.scheduled_for else ""
            content = post.content.replace('"', '""').replace('\n', ' ')
            hashtags = " ".join(f"#{tag}" for tag in post.hashtags)
            media = " | ".join(post.media_urls)
            
            lines.append(f'"{date}","{post.platform.value}","{content}","{hashtags}","{media}"')
        
        return "\n".join(lines)
