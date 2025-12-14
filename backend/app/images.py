"""
Waiting The Longest™ - Image Utilities
========================================
Image processing and optimization utilities.
"""

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlencode, urlparse


logger = logging.getLogger(__name__)


# =============================================================================
# Image Configuration
# =============================================================================

class ImageSize(str, Enum):
    """Predefined image sizes."""
    THUMBNAIL = "thumbnail"  # 150x150
    SMALL = "small"          # 300x300
    MEDIUM = "medium"        # 600x600
    LARGE = "large"          # 1200x1200
    ORIGINAL = "original"


@dataclass
class ImageDimensions:
    """Image dimensions configuration."""
    width: int
    height: int
    
    SIZE_MAP = {
        ImageSize.THUMBNAIL: (150, 150),
        ImageSize.SMALL: (300, 300),
        ImageSize.MEDIUM: (600, 600),
        ImageSize.LARGE: (1200, 1200),
    }
    
    @classmethod
    def for_size(cls, size: ImageSize) -> "ImageDimensions":
        """Get dimensions for a size preset."""
        if size == ImageSize.ORIGINAL:
            return cls(0, 0)  # No resizing
        
        width, height = cls.SIZE_MAP.get(size, (600, 600))
        return cls(width, height)


# =============================================================================
# Image URL Builder
# =============================================================================

class ImageURLBuilder:
    """
    Build optimized image URLs using CDN/image optimization services.
    """
    
    # Supported CDN providers
    PROVIDERS = {
        "cloudinary": "https://res.cloudinary.com/{cloud_name}/image/fetch",
        "imgix": "https://{domain}.imgix.net",
        "vercel": "/_vercel/image",
    }
    
    def __init__(
        self,
        provider: str = "vercel",
        cloud_name: str | None = None,
        domain: str | None = None,
    ):
        self.provider = provider
        self.cloud_name = cloud_name
        self.domain = domain
    
    def build_url(
        self,
        source_url: str,
        size: ImageSize = ImageSize.MEDIUM,
        quality: int = 80,
        format: str = "auto",
    ) -> str:
        """
        Build an optimized image URL.
        
        Args:
            source_url: Original image URL
            size: Desired size preset
            quality: Image quality (1-100)
            format: Output format (auto, webp, avif, etc.)
        
        Returns:
            Optimized image URL
        """
        if not source_url:
            return self._get_placeholder(size)
        
        dimensions = ImageDimensions.for_size(size)
        
        if self.provider == "vercel":
            return self._build_vercel_url(source_url, dimensions, quality)
        elif self.provider == "cloudinary":
            return self._build_cloudinary_url(source_url, dimensions, quality, format)
        elif self.provider == "imgix":
            return self._build_imgix_url(source_url, dimensions, quality, format)
        
        # Fallback: return original URL
        return source_url
    
    def _build_vercel_url(
        self,
        source_url: str,
        dimensions: ImageDimensions,
        quality: int,
    ) -> str:
        """Build Vercel Image Optimization URL."""
        params = {
            "url": source_url,
            "q": quality,
        }
        
        if dimensions.width > 0:
            params["w"] = dimensions.width
        
        return f"/_vercel/image?{urlencode(params)}"
    
    def _build_cloudinary_url(
        self,
        source_url: str,
        dimensions: ImageDimensions,
        quality: int,
        format: str,
    ) -> str:
        """Build Cloudinary URL."""
        if not self.cloud_name:
            return source_url
        
        transformations = [
            f"w_{dimensions.width}" if dimensions.width > 0 else "",
            f"h_{dimensions.height}" if dimensions.height > 0 else "",
            f"q_{quality}",
            f"f_{format}",
            "c_fill",
        ]
        
        transform_str = ",".join(filter(None, transformations))
        base = self.PROVIDERS["cloudinary"].format(cloud_name=self.cloud_name)
        
        return f"{base}/{transform_str}/{source_url}"
    
    def _build_imgix_url(
        self,
        source_url: str,
        dimensions: ImageDimensions,
        quality: int,
        format: str,
    ) -> str:
        """Build imgix URL."""
        if not self.domain:
            return source_url
        
        params = {
            "w": dimensions.width,
            "h": dimensions.height,
            "q": quality,
            "auto": "format",
            "fit": "crop",
        }
        
        # Remove zero dimensions
        params = {k: v for k, v in params.items() if v}
        
        base = self.PROVIDERS["imgix"].format(domain=self.domain)
        path = urlparse(source_url).path
        
        return f"{base}{path}?{urlencode(params)}"
    
    def _get_placeholder(self, size: ImageSize) -> str:
        """Get placeholder image URL for missing images."""
        dimensions = ImageDimensions.for_size(size)
        
        # Use a placeholder service
        return f"https://placehold.co/{dimensions.width}x{dimensions.height}/e0e0e0/666?text=No+Photo"


# =============================================================================
# Responsive Image Generator
# =============================================================================

class ResponsiveImageGenerator:
    """
    Generate srcset and sizes attributes for responsive images.
    """
    
    BREAKPOINTS = [320, 640, 768, 1024, 1280, 1536]
    
    def __init__(self, url_builder: ImageURLBuilder | None = None):
        self.url_builder = url_builder or ImageURLBuilder()
    
    def generate_srcset(self, source_url: str) -> str:
        """
        Generate srcset attribute value.
        
        Returns:
            srcset string for responsive images
        """
        srcset_items = []
        
        for width in self.BREAKPOINTS:
            # Map width to size preset
            if width <= 320:
                size = ImageSize.THUMBNAIL
            elif width <= 640:
                size = ImageSize.SMALL
            elif width <= 1024:
                size = ImageSize.MEDIUM
            else:
                size = ImageSize.LARGE
            
            url = self.url_builder.build_url(source_url, size)
            srcset_items.append(f"{url} {width}w")
        
        return ", ".join(srcset_items)
    
    def generate_sizes(
        self,
        mobile: str = "100vw",
        tablet: str = "50vw",
        desktop: str = "33vw",
    ) -> str:
        """
        Generate sizes attribute value.
        
        Returns:
            sizes string for responsive images
        """
        return f"(max-width: 640px) {mobile}, (max-width: 1024px) {tablet}, {desktop}"
    
    def generate_picture_sources(
        self,
        source_url: str,
        formats: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """
        Generate source elements for picture element.
        
        Returns:
            List of source attributes
        """
        formats = formats or ["avif", "webp"]
        sources = []
        
        for fmt in formats:
            srcset = self.generate_srcset(source_url)
            sources.append({
                "type": f"image/{fmt}",
                "srcset": srcset,
            })
        
        return sources


# =============================================================================
# Image Cache
# =============================================================================

class ImageCache:
    """
    Simple image URL cache for optimized URLs.
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, str] = {}
        self._max_size = max_size
    
    def _make_key(self, url: str, size: ImageSize) -> str:
        """Create cache key."""
        return hashlib.md5(f"{url}:{size.value}".encode()).hexdigest()
    
    def get(self, url: str, size: ImageSize) -> str | None:
        """Get cached URL."""
        key = self._make_key(url, size)
        return self._cache.get(key)
    
    def set(self, url: str, size: ImageSize, optimized_url: str):
        """Cache optimized URL."""
        if len(self._cache) >= self._max_size:
            # Simple eviction: clear half
            keys = list(self._cache.keys())[:len(self._cache) // 2]
            for k in keys:
                del self._cache[k]
        
        key = self._make_key(url, size)
        self._cache[key] = optimized_url
    
    def invalidate(self, url: str | None = None):
        """Invalidate cache entries."""
        if url:
            # Remove all sizes for this URL
            prefix = hashlib.md5(url.encode()).hexdigest()[:8]
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
        else:
            self._cache.clear()


# =============================================================================
# Global Instance
# =============================================================================

_image_builder: ImageURLBuilder | None = None


def get_image_builder() -> ImageURLBuilder:
    """Get the global image URL builder."""
    global _image_builder
    if _image_builder is None:
        _image_builder = ImageURLBuilder()
    return _image_builder


def optimize_image_url(
    url: str,
    size: ImageSize = ImageSize.MEDIUM,
    **kwargs,
) -> str:
    """Convenience function to optimize an image URL."""
    return get_image_builder().build_url(url, size, **kwargs)


# =============================================================================
# Animal Photo Utilities
# =============================================================================

def get_animal_photos(animal: Any) -> list[str]:
    """Extract photo URLs from animal data."""
    photos = []
    
    # Handle different data structures
    if hasattr(animal, "photos"):
        if isinstance(animal.photos, list):
            photos = animal.photos
        elif isinstance(animal.photos, str):
            photos = [animal.photos]
    elif hasattr(animal, "photo_url") and animal.photo_url:
        photos = [animal.photo_url]
    elif isinstance(animal, dict):
        if "photos" in animal:
            photos = animal["photos"] if isinstance(animal["photos"], list) else [animal["photos"]]
        elif "photo_url" in animal:
            photos = [animal["photo_url"]]
    
    # Filter out empty/invalid URLs
    return [p for p in photos if p and isinstance(p, str)]


def get_primary_photo(animal: Any, size: ImageSize = ImageSize.MEDIUM) -> str:
    """Get the primary (first) photo for an animal, optimized."""
    photos = get_animal_photos(animal)
    
    if photos:
        return optimize_image_url(photos[0], size)
    
    return get_image_builder()._get_placeholder(size)
