"""
Waiting The Longest™ - Image Utilities
=======================================
Utilities for processing and optimizing animal photos.
"""

import os
import hashlib
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
from io import BytesIO

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """Information about a processed image."""
    original_url: str
    processed_url: Optional[str]
    width: Optional[int]
    height: Optional[int]
    file_size: Optional[int]
    content_type: Optional[str]
    alt_text: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_url": self.original_url,
            "processed_url": self.processed_url or self.original_url,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "alt_text": self.alt_text,
        }


class ImageProcessor:
    """
    Process and optimize animal photos.
    
    Features:
    - URL validation and normalization
    - Placeholder generation for missing images
    - Responsive image srcset generation
    - Alt text generation
    """
    
    # Default placeholder images by species
    PLACEHOLDER_IMAGES = {
        "dog": "https://placedog.net/300/300",
        "cat": "https://placekitten.com/300/300",
        "rabbit": "/images/placeholder-rabbit.jpg",
        "bird": "/images/placeholder-bird.jpg",
        "other": "/images/placeholder-animal.jpg",
    }
    
    # Common image CDN domains for optimization
    CDN_DOMAINS = [
        "cloudinary.com",
        "imgix.net",
        "imagekit.io",
        "cloudflare.com",
    ]
    
    # Standard thumbnail sizes
    THUMBNAIL_SIZES = {
        "small": (150, 150),
        "medium": (300, 300),
        "large": (600, 600),
        "hero": (1200, 800),
    }
    
    def __init__(self, cdn_base_url: Optional[str] = None):
        """
        Initialize image processor.
        
        Args:
            cdn_base_url: Optional CDN base URL for processed images
        """
        self.cdn_base_url = cdn_base_url
    
    def validate_url(self, url: str) -> bool:
        """Check if a URL is valid and accessible."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize and clean up an image URL."""
        if not url:
            return ""
        
        url = url.strip()
        
        # Add scheme if missing
        if url.startswith("//"):
            url = "https:" + url
        
        # Handle relative URLs (shouldn't happen in production)
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        return url
    
    def get_placeholder(self, species: str = "other", name: str = "") -> str:
        """Get a placeholder image URL for a species."""
        species_lower = species.lower() if species else "other"
        placeholder_url = self.PLACEHOLDER_IMAGES.get(
            species_lower,
            self.PLACEHOLDER_IMAGES["other"]
        )
        
        # For external placeholders, add some variation based on name
        if "placedog" in placeholder_url or "placekitten" in placeholder_url:
            name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
            size = 300 + (int(name_hash[:2], 16) % 100)
            if "placedog" in placeholder_url:
                placeholder_url = f"https://placedog.net/{size}/{size}"
            else:
                placeholder_url = f"https://placekitten.com/{size}/{size}"
        
        return placeholder_url
    
    def generate_alt_text(
        self,
        name: str,
        species: str,
        breed: Optional[str] = None,
        color: Optional[str] = None,
    ) -> str:
        """Generate descriptive alt text for accessibility."""
        parts = []
        
        if color:
            parts.append(color.lower())
        
        if breed:
            parts.append(breed)
        elif species:
            parts.append(species)
        
        parts.append(f"named {name}")
        
        return " ".join(parts).capitalize()
    
    def generate_srcset(
        self,
        original_url: str,
        sizes: Optional[List[str]] = None,
    ) -> str:
        """
        Generate responsive srcset for an image.
        
        Returns srcset string for responsive images.
        """
        if not original_url or not self.validate_url(original_url):
            return ""
        
        if sizes is None:
            sizes = ["small", "medium", "large"]
        
        # Check if URL is from a CDN that supports transformations
        parsed = urlparse(original_url)
        is_cdn = any(cdn in parsed.netloc for cdn in self.CDN_DOMAINS)
        
        if is_cdn:
            # Generate CDN-specific transformed URLs
            srcset_parts = []
            for size in sizes:
                width, height = self.THUMBNAIL_SIZES.get(size, (300, 300))
                # This is a simplified example - actual implementation depends on CDN
                transformed_url = f"{original_url}?w={width}&h={height}&fit=crop"
                srcset_parts.append(f"{transformed_url} {width}w")
            return ", ".join(srcset_parts)
        
        # For non-CDN images, just return the original
        return original_url
    
    def process_animal_image(
        self,
        url: Optional[str],
        name: str,
        species: str,
        breed: Optional[str] = None,
    ) -> ImageInfo:
        """
        Process an animal image URL.
        
        Validates, normalizes, and prepares image for display.
        """
        alt_text = self.generate_alt_text(name, species, breed)
        
        if not url:
            placeholder = self.get_placeholder(species, name)
            return ImageInfo(
                original_url=placeholder,
                processed_url=placeholder,
                width=300,
                height=300,
                file_size=None,
                content_type="image/jpeg",
                alt_text=alt_text,
            )
        
        normalized_url = self.normalize_url(url)
        
        if not self.validate_url(normalized_url):
            placeholder = self.get_placeholder(species, name)
            return ImageInfo(
                original_url=url,
                processed_url=placeholder,
                width=300,
                height=300,
                file_size=None,
                content_type="image/jpeg",
                alt_text=alt_text,
            )
        
        return ImageInfo(
            original_url=url,
            processed_url=normalized_url,
            width=None,  # Would need to fetch to determine
            height=None,
            file_size=None,
            content_type=None,
            alt_text=alt_text,
        )
    
    def generate_gallery_data(
        self,
        primary_url: Optional[str],
        additional_urls: List[str],
        name: str,
        species: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate gallery data for multiple animal photos.
        
        Returns list of processed image data for gallery display.
        """
        images = []
        
        # Process primary image
        if primary_url:
            primary_info = self.process_animal_image(primary_url, name, species)
            primary_data = primary_info.to_dict()
            primary_data["is_primary"] = True
            images.append(primary_data)
        
        # Process additional images
        for i, url in enumerate(additional_urls):
            if url and url != primary_url:  # Avoid duplicates
                info = self.process_animal_image(url, name, species)
                data = info.to_dict()
                data["is_primary"] = False
                data["position"] = i + 1
                images.append(data)
        
        return images


class LazyLoadHelper:
    """Helper for implementing lazy loading of images."""
    
    @staticmethod
    def generate_blur_placeholder(color: str = "#e0e0e0") -> str:
        """Generate a simple colored placeholder for blur-up loading."""
        # Returns a tiny SVG as a data URI
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">
            <rect width="10" height="10" fill="{color}"/>
        </svg>'''
        # In production, encode as base64 data URI
        return color
    
    @staticmethod
    def get_loading_attributes() -> Dict[str, str]:
        """Get HTML attributes for lazy loading."""
        return {
            "loading": "lazy",
            "decoding": "async",
        }
    
    @staticmethod
    def generate_img_tag(
        src: str,
        alt: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        lazy: bool = True,
        class_name: str = "",
    ) -> str:
        """Generate an HTML img tag with proper attributes."""
        attrs = [f'src="{src}"', f'alt="{alt}"']
        
        if width:
            attrs.append(f'width="{width}"')
        if height:
            attrs.append(f'height="{height}"')
        if lazy:
            attrs.append('loading="lazy"')
            attrs.append('decoding="async"')
        if class_name:
            attrs.append(f'class="{class_name}"')
        
        return f'<img {" ".join(attrs)}>'


# Convenience functions
def get_animal_image_url(
    photo_url: Optional[str],
    species: str = "other",
    name: str = "Animal",
) -> str:
    """Get the display URL for an animal photo."""
    processor = ImageProcessor()
    info = processor.process_animal_image(photo_url, name, species)
    return info.processed_url or info.original_url


def generate_animal_alt_text(name: str, species: str, breed: Optional[str] = None) -> str:
    """Generate alt text for an animal photo."""
    processor = ImageProcessor()
    return processor.generate_alt_text(name, species, breed)
