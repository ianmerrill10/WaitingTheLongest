"""
===============================================================================
Waiting The Longest™ - Social Media Video Generator
===============================================================================
Generates TikTok/Instagram Reels style videos featuring animals who have
waited the longest. These videos are crucial for viral growth!

Dependencies:
    pip install moviepy pillow numpy

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import os
import logging
from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass
import tempfile

try:
    from moviepy.editor import (
        ImageClip, TextClip, CompositeVideoClip,
        concatenate_videoclips, AudioFileClip
    )
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logging.warning("MoviePy not installed. Video generation disabled.")

from ..app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VideoConfig:
    """Configuration for video generation"""
    width: int = 1080
    height: int = 1920  # 9:16 aspect ratio for TikTok/Reels
    fps: int = 30
    duration_per_image: float = 3.0
    transition_duration: float = 0.5

    # Brand colors
    primary_color: str = "#E86C3A"
    secondary_color: str = "#4A90A4"
    text_color: str = "#FFFFFF"

    # Fonts
    font_name: str = "Arial-Bold"
    title_font_size: int = 80
    subtitle_font_size: int = 50
    days_font_size: int = 120


class SocialVideoGenerator:
    """
    Generates social media videos for promoting animals.

    Video format: 9:16 vertical (TikTok/Instagram Reels)

    Features:
    - Photo slideshow of the animal
    - "X Days Waiting" prominent overlay
    - Animal name and breed
    - Call to action
    - Brand watermark
    """

    def __init__(self, config: Optional[VideoConfig] = None):
        self.config = config or VideoConfig()
        self.output_dir = settings.VIDEO_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_video(
        self,
        animal_id: int,
        name: str,
        days_waiting: int,
        breed: str,
        photos: List[str],
        shelter_name: str,
        city: str = "",
        state: str = ""
    ) -> Optional[str]:
        """
        Generate a promotional video for an animal.

        Returns:
            Path to generated video file, or None if failed
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("MoviePy not available. Cannot generate video.")
            return None

        if not photos:
            logger.warning(f"No photos for animal {animal_id}. Skipping video.")
            return None

        try:
            clips = []

            # Generate intro clip
            intro = self._create_intro_clip(name, days_waiting)
            clips.append(intro)

            # Generate photo clips
            for i, photo_url in enumerate(photos[:5]):  # Max 5 photos
                clip = self._create_photo_clip(
                    photo_url,
                    name,
                    days_waiting,
                    breed if i == 0 else None
                )
                if clip:
                    clips.append(clip)

            # Generate outro clip
            outro = self._create_outro_clip(shelter_name, city, state)
            clips.append(outro)

            # Concatenate all clips
            final_video = concatenate_videoclips(clips, method="compose")

            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                self.output_dir,
                f"wtl_{animal_id}_{timestamp}.mp4"
            )

            # Write video
            final_video.write_videofile(
                output_path,
                fps=self.config.fps,
                codec="libx264",
                audio=False,  # Add audio separately if needed
                preset="medium",
                threads=4
            )

            # Cleanup
            final_video.close()
            for clip in clips:
                clip.close()

            logger.info(f"Generated video: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate video for animal {animal_id}: {e}")
            return None

    def _create_intro_clip(self, name: str, days_waiting: int) -> ImageClip:
        """Create intro clip with days waiting prominently displayed"""

        # Create background image
        img = Image.new('RGB', (self.config.width, self.config.height),
                       color=self.config.primary_color)
        draw = ImageDraw.Draw(img)

        # Add text
        self._add_centered_text(
            draw,
            f"{days_waiting}",
            self.config.height // 3,
            self.config.days_font_size,
            self.config.text_color
        )

        self._add_centered_text(
            draw,
            "DAYS WAITING",
            self.config.height // 3 + 150,
            self.config.subtitle_font_size,
            self.config.text_color
        )

        self._add_centered_text(
            draw,
            name.upper(),
            self.config.height // 2 + 100,
            self.config.title_font_size,
            self.config.text_color
        )

        self._add_centered_text(
            draw,
            "needs a home",
            self.config.height // 2 + 200,
            self.config.subtitle_font_size,
            self.config.text_color
        )

        # Add watermark
        self._add_watermark(draw)

        # Convert to clip
        return ImageClip(np.array(img)).set_duration(self.config.duration_per_image)

    def _create_photo_clip(
        self,
        photo_url: str,
        name: str,
        days_waiting: int,
        breed: Optional[str] = None
    ) -> Optional[ImageClip]:
        """Create clip from a photo with overlay text"""
        try:
            import requests
            from io import BytesIO

            # Download image
            response = requests.get(photo_url, timeout=10)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content))
            img = img.convert('RGB')

            # Resize to fit video dimensions
            img = self._resize_and_crop(img)

            draw = ImageDraw.Draw(img)

            # Add gradient overlay at bottom
            self._add_gradient_overlay(img)
            draw = ImageDraw.Draw(img)  # Recreate draw object

            # Add text overlay
            y_pos = self.config.height - 400

            self._add_centered_text(
                draw,
                f"{days_waiting} Days Waiting",
                y_pos,
                60,
                self.config.text_color
            )

            if breed:
                self._add_centered_text(
                    draw,
                    breed,
                    y_pos + 80,
                    40,
                    self.config.text_color
                )

            # Add watermark
            self._add_watermark(draw)

            return ImageClip(np.array(img)).set_duration(self.config.duration_per_image)

        except Exception as e:
            logger.warning(f"Failed to process photo {photo_url}: {e}")
            return None

    def _create_outro_clip(
        self,
        shelter_name: str,
        city: str,
        state: str
    ) -> ImageClip:
        """Create outro clip with call to action"""

        img = Image.new('RGB', (self.config.width, self.config.height),
                       color=self.config.secondary_color)
        draw = ImageDraw.Draw(img)

        self._add_centered_text(
            draw,
            "ADOPT TODAY",
            self.config.height // 3,
            self.config.title_font_size,
            self.config.text_color
        )

        self._add_centered_text(
            draw,
            "Because Every Day Matters",
            self.config.height // 3 + 120,
            self.config.subtitle_font_size,
            self.config.text_color
        )

        location = f"{city}, {state}".strip(", ")
        if location:
            self._add_centered_text(
                draw,
                f"{location}",
                self.config.height // 2 + 50,
                40,
                self.config.text_color
            )

        self._add_centered_text(
            draw,
            shelter_name,
            self.config.height // 2 + 120,
            40,
            self.config.text_color
        )

        self._add_centered_text(
            draw,
            "WaitingTheLongest.com",
            self.config.height - 200,
            50,
            self.config.text_color
        )

        self._add_watermark(draw)

        return ImageClip(np.array(img)).set_duration(self.config.duration_per_image + 1)

    def _resize_and_crop(self, img: Image.Image) -> Image.Image:
        """Resize and crop image to fit video dimensions"""
        target_ratio = self.config.width / self.config.height
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            # Image is wider - crop sides
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            # Image is taller - crop top/bottom
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        return img.resize((self.config.width, self.config.height), Image.LANCZOS)

    def _add_gradient_overlay(self, img: Image.Image):
        """Add gradient overlay at bottom of image for text readability"""
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        gradient_height = 500
        for i in range(gradient_height):
            alpha = int(200 * (i / gradient_height))
            y = self.config.height - gradient_height + i
            draw.line([(0, y), (self.config.width, y)], fill=(0, 0, 0, alpha))

        img.paste(Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB'))

    def _add_centered_text(
        self,
        draw: ImageDraw.Draw,
        text: str,
        y: int,
        font_size: int,
        color: str
    ):
        """Add centered text to image"""
        try:
            font = ImageFont.truetype(self.config.font_name, font_size)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.config.width - text_width) // 2

        # Add shadow
        draw.text((x + 2, y + 2), text, font=font, fill="#000000")
        draw.text((x, y), text, font=font, fill=color)

    def _add_watermark(self, draw: ImageDraw.Draw):
        """Add brand watermark"""
        try:
            font = ImageFont.truetype(self.config.font_name, 30)
        except:
            font = ImageFont.load_default()

        watermark = "WaitingTheLongest.com"
        bbox = draw.textbbox((0, 0), watermark, font=font)
        text_width = bbox[2] - bbox[0]

        x = self.config.width - text_width - 30
        y = 50

        draw.text((x, y), watermark, font=font, fill="#FFFFFF80")


def generate_animal_video(db, animal_id: int) -> Optional[str]:
    """
    Convenience function to generate video for an animal.

    Fetches animal data from database and generates video.
    """
    from ..app.crud import get_animal_detail

    animal = get_animal_detail(db, animal_id)
    if not animal:
        logger.error(f"Animal {animal_id} not found")
        return None

    generator = SocialVideoGenerator()

    return generator.generate_video(
        animal_id=animal.id,
        name=animal.canonical_name or "Sweet Pet",
        days_waiting=animal.days_waiting,
        breed=animal.breed_primary or animal.species,
        photos=animal.photos,
        shelter_name=animal.shelter_info.get("name", "") if animal.shelter_info else "",
        city=animal.shelter_info.get("city", "") if animal.shelter_info else "",
        state=animal.shelter_info.get("state", "") if animal.shelter_info else ""
    )
