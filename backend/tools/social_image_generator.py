"""
===============================================================================
Waiting The Longest™ - Social Share Image Generator
===============================================================================
Purpose: Generate Open Graph images for social sharing.
         Creates branded preview images for pet profiles.

Author: Waiting The Longest™ Development Team
Dependencies: PIL/Pillow
===============================================================================
"""

import io
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageFont = None

logger = logging.getLogger(__name__)


class SocialImageGenerator:
    """Generate Open Graph images for social sharing."""
    
    # Image dimensions (Twitter/Facebook recommended)
    WIDTH = 1200
    HEIGHT = 630
    
    # Brand colors (RGB)
    PRIMARY_COLOR = (37, 99, 235)  # #2563EB
    SECONDARY_COLOR = (124, 58, 237)  # #7C3AED
    WHITE = (255, 255, 255)
    TEXT_COLOR = (31, 41, 55)  # #1F2937
    TEXT_LIGHT = (107, 114, 128)  # #6B7280
    
    @classmethod
    def generate_animal_card(
        cls,
        animal: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate an OG image for an animal profile.
        
        Args:
            animal: Animal data dict with name, breed, days_waiting, photo_url, etc.
            output_path: Optional file path to save image
            
        Returns:
            PNG image bytes, or None if PIL not available
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL/Pillow not installed. Cannot generate social images.")
            return None
        
        # Create base image with gradient background
        img = Image.new('RGB', (cls.WIDTH, cls.HEIGHT), cls.PRIMARY_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        for y in range(cls.HEIGHT):
            ratio = y / cls.HEIGHT
            r = int(cls.PRIMARY_COLOR[0] * (1 - ratio) + cls.SECONDARY_COLOR[0] * ratio)
            g = int(cls.PRIMARY_COLOR[1] * (1 - ratio) + cls.SECONDARY_COLOR[1] * ratio)
            b = int(cls.PRIMARY_COLOR[2] * (1 - ratio) + cls.SECONDARY_COLOR[2] * ratio)
            draw.line([(0, y), (cls.WIDTH, y)], fill=(r, g, b))
        
        # Try to load fonts (fallback to default if not available)
        try:
            # These fonts should be available on most systems
            title_font = ImageFont.truetype("arial.ttf", 48)
            subtitle_font = ImageFont.truetype("arial.ttf", 32)
            badge_font = ImageFont.truetype("arialbd.ttf", 36)
            small_font = ImageFont.truetype("arial.ttf", 24)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            subtitle_font = title_font
            badge_font = title_font
            small_font = title_font
        
        # Draw white card background
        card_margin = 40
        card_height = cls.HEIGHT - card_margin * 2
        draw.rounded_rectangle(
            [card_margin, card_margin, cls.WIDTH - card_margin, cls.HEIGHT - card_margin],
            radius=20,
            fill=cls.WHITE
        )
        
        # Pet name
        name = animal.get('canonical_name') or animal.get('name') or 'Meet This Pet'
        text_x = card_margin + 60
        text_y = card_margin + 60
        draw.text((text_x, text_y), name, fill=cls.TEXT_COLOR, font=title_font)
        
        # Breed info
        breed = animal.get('breed_primary') or animal.get('species', 'Pet').title()
        location = f"{animal.get('city', '')} {animal.get('state', '')}".strip()
        subtitle = f"{breed}" + (f" • {location}" if location else "")
        draw.text((text_x, text_y + 60), subtitle, fill=cls.TEXT_LIGHT, font=subtitle_font)
        
        # Days waiting badge
        days = animal.get('days_waiting', 0)
        badge_text = f"Waiting {days} Days"
        badge_x = text_x
        badge_y = text_y + 140
        
        # Badge background
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_width = bbox[2] - bbox[0] + 40
        badge_height = bbox[3] - bbox[1] + 20
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
            radius=badge_height // 2,
            fill=cls.PRIMARY_COLOR
        )
        draw.text((badge_x + 20, badge_y + 10), badge_text, fill=cls.WHITE, font=badge_font)
        
        # Mission tagline
        tagline = "Because Every Day Matters"
        draw.text(
            (text_x, cls.HEIGHT - card_margin - 80),
            tagline,
            fill=cls.TEXT_LIGHT,
            font=small_font
        )
        
        # Logo/brand
        brand = "Waiting The Longest™"
        draw.text(
            (cls.WIDTH - card_margin - 60 - draw.textlength(brand, font=small_font), 
             cls.HEIGHT - card_margin - 80),
            brand,
            fill=cls.PRIMARY_COLOR,
            font=small_font
        )
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        
        # Optionally save to file
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"Social image saved to {output_path}")
        
        return image_bytes
    
    @classmethod
    def generate_stats_card(
        cls,
        stats: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate an OG image showing platform stats.
        
        Args:
            stats: Stats dict with total_animals, longest_wait_days, etc.
            output_path: Optional file path to save image
            
        Returns:
            PNG image bytes
        """
        if not PIL_AVAILABLE:
            return None
        
        img = Image.new('RGB', (cls.WIDTH, cls.HEIGHT), cls.WHITE)
        draw = ImageDraw.Draw(img)
        
        # Gradient header
        header_height = 200
        for y in range(header_height):
            ratio = y / header_height
            r = int(cls.PRIMARY_COLOR[0] * (1 - ratio) + cls.SECONDARY_COLOR[0] * ratio)
            g = int(cls.PRIMARY_COLOR[1] * (1 - ratio) + cls.SECONDARY_COLOR[1] * ratio)
            b = int(cls.PRIMARY_COLOR[2] * (1 - ratio) + cls.SECONDARY_COLOR[2] * ratio)
            draw.line([(0, y), (cls.WIDTH, y)], fill=(r, g, b))
        
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 48)
            subtitle_font = ImageFont.truetype("arial.ttf", 28)
            stat_font = ImageFont.truetype("arialbd.ttf", 72)
            label_font = ImageFont.truetype("arial.ttf", 24)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            subtitle_font = title_font
            stat_font = title_font
            label_font = title_font
        
        # Title
        title = "Waiting The Longest™"
        title_width = draw.textlength(title, font=title_font)
        draw.text(((cls.WIDTH - title_width) // 2, 60), title, fill=cls.WHITE, font=title_font)
        
        # Subtitle
        subtitle = "Because Every Day Matters"
        subtitle_width = draw.textlength(subtitle, font=subtitle_font)
        draw.text(((cls.WIDTH - subtitle_width) // 2, 120), subtitle, fill=cls.WHITE, font=subtitle_font)
        
        # Stats
        stat_y = header_height + 80
        stat_spacing = cls.WIDTH // 3
        
        stat_items = [
            (str(stats.get('available_animals', 0)), "Animals Waiting"),
            (str(stats.get('longest_wait_days', 0)), "Days Longest Wait"),
            (str(stats.get('success_stories', 0)), "Happy Adoptions"),
        ]
        
        for i, (value, label) in enumerate(stat_items):
            x = stat_spacing // 2 + i * stat_spacing
            
            # Value
            value_width = draw.textlength(value, font=stat_font)
            draw.text((x - value_width // 2, stat_y), value, fill=cls.PRIMARY_COLOR, font=stat_font)
            
            # Label
            label_width = draw.textlength(label, font=label_font)
            draw.text((x - label_width // 2, stat_y + 80), label, fill=cls.TEXT_LIGHT, font=label_font)
        
        # CTA
        cta = "Help a pet find their forever home today"
        cta_width = draw.textlength(cta, font=subtitle_font)
        draw.text(((cls.WIDTH - cta_width) // 2, cls.HEIGHT - 100), cta, fill=cls.TEXT_COLOR, font=subtitle_font)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
        
        return buffer.getvalue()


if __name__ == "__main__":
    # Test image generation
    test_animal = {
        "canonical_name": "Buddy",
        "breed_primary": "German Shepherd",
        "days_waiting": 500,
        "city": "Austin",
        "state": "TX"
    }
    
    test_stats = {
        "available_animals": 500,
        "longest_wait_days": 500,
        "success_stories": 250
    }
    
    generator = SocialImageGenerator()
    
    # Generate test images
    animal_img = generator.generate_animal_card(test_animal, "test_animal_og.png")
    stats_img = generator.generate_stats_card(test_stats, "test_stats_og.png")
    
    if animal_img:
        print(f"Animal card generated: {len(animal_img)} bytes")
    if stats_img:
        print(f"Stats card generated: {len(stats_img)} bytes")
