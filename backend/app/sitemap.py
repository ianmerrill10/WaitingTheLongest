"""
Waiting The Longest™ - Sitemap Generator
==========================================
Dynamic sitemap generation for SEO.
"""

from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator
import xml.etree.ElementTree as ET


# =============================================================================
# Sitemap Configuration
# =============================================================================

class ChangeFrequency(str, Enum):
    """How frequently a page is likely to change."""
    ALWAYS = "always"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    NEVER = "never"


@dataclass
class SitemapURL:
    """A single URL entry in the sitemap."""
    
    loc: str                           # URL location
    lastmod: datetime | date | None = None  # Last modification date
    changefreq: ChangeFrequency | None = None
    priority: float | None = None      # 0.0 to 1.0
    
    def to_xml_element(self) -> ET.Element:
        """Convert to XML element."""
        url = ET.Element("url")
        
        loc = ET.SubElement(url, "loc")
        loc.text = self.loc
        
        if self.lastmod:
            lastmod = ET.SubElement(url, "lastmod")
            if isinstance(self.lastmod, datetime):
                lastmod.text = self.lastmod.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            else:
                lastmod.text = self.lastmod.strftime("%Y-%m-%d")
        
        if self.changefreq:
            changefreq = ET.SubElement(url, "changefreq")
            changefreq.text = self.changefreq.value
        
        if self.priority is not None:
            priority = ET.SubElement(url, "priority")
            priority.text = f"{self.priority:.1f}"
        
        return url


# =============================================================================
# Sitemap Generator
# =============================================================================

class SitemapGenerator:
    """
    Generate XML sitemaps for the website.
    """
    
    SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
    MAX_URLS_PER_SITEMAP = 50000
    
    def __init__(self, base_url: str):
        """
        Initialize the sitemap generator.
        
        Args:
            base_url: Base URL of the website (e.g., https://waitingthelongest.com)
        """
        self.base_url = base_url.rstrip("/")
        self.urls: list[SitemapURL] = []
    
    def add_url(
        self,
        path: str,
        lastmod: datetime | date | None = None,
        changefreq: ChangeFrequency | None = None,
        priority: float | None = None,
    ) -> "SitemapGenerator":
        """Add a URL to the sitemap."""
        url = SitemapURL(
            loc=f"{self.base_url}{path}",
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
        )
        self.urls.append(url)
        return self
    
    def add_static_pages(self) -> "SitemapGenerator":
        """Add standard static pages."""
        static_pages = [
            ("/", ChangeFrequency.HOURLY, 1.0),
            ("/about", ChangeFrequency.MONTHLY, 0.5),
            ("/how-it-works", ChangeFrequency.MONTHLY, 0.6),
            ("/shelters", ChangeFrequency.DAILY, 0.7),
            ("/articles", ChangeFrequency.WEEKLY, 0.6),
            ("/contact", ChangeFrequency.MONTHLY, 0.4),
            ("/privacy", ChangeFrequency.YEARLY, 0.2),
            ("/terms", ChangeFrequency.YEARLY, 0.2),
        ]
        
        for path, freq, priority in static_pages:
            self.add_url(path, changefreq=freq, priority=priority)
        
        return self
    
    def add_animals(
        self,
        animals: list[Any],
        id_field: str = "id",
        updated_field: str | None = "updated_at",
    ) -> "SitemapGenerator":
        """
        Add animal profile pages to sitemap.
        
        Args:
            animals: List of animal objects/dicts
            id_field: Field name for animal ID
            updated_field: Field name for last updated date
        """
        for animal in animals:
            if isinstance(animal, dict):
                animal_id = animal.get(id_field)
                lastmod = animal.get(updated_field) if updated_field else None
            else:
                animal_id = getattr(animal, id_field, None)
                lastmod = getattr(animal, updated_field, None) if updated_field else None
            
            if animal_id:
                self.add_url(
                    f"/animals/{animal_id}",
                    lastmod=lastmod,
                    changefreq=ChangeFrequency.WEEKLY,
                    priority=0.8,
                )
        
        return self
    
    def add_shelters(
        self,
        shelters: list[Any],
        id_field: str = "id",
    ) -> "SitemapGenerator":
        """Add shelter pages to sitemap."""
        for shelter in shelters:
            if isinstance(shelter, dict):
                shelter_id = shelter.get(id_field)
            else:
                shelter_id = getattr(shelter, id_field, None)
            
            if shelter_id:
                self.add_url(
                    f"/shelters/{shelter_id}",
                    changefreq=ChangeFrequency.WEEKLY,
                    priority=0.6,
                )
        
        return self
    
    def generate_xml(self) -> str:
        """Generate the sitemap XML string."""
        urlset = ET.Element("urlset")
        urlset.set("xmlns", self.SITEMAP_NS)
        
        for url in self.urls[:self.MAX_URLS_PER_SITEMAP]:
            urlset.append(url.to_xml_element())
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            urlset,
            encoding="unicode",
        )
    
    def generate_index(self, sitemap_paths: list[str]) -> str:
        """
        Generate a sitemap index file for multiple sitemaps.
        
        Args:
            sitemap_paths: List of sitemap paths (e.g., ["/sitemap-animals.xml"])
        """
        sitemapindex = ET.Element("sitemapindex")
        sitemapindex.set("xmlns", self.SITEMAP_NS)
        
        for path in sitemap_paths:
            sitemap = ET.SubElement(sitemapindex, "sitemap")
            loc = ET.SubElement(sitemap, "loc")
            loc.text = f"{self.base_url}{path}"
            lastmod = ET.SubElement(sitemap, "lastmod")
            lastmod.text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            sitemapindex,
            encoding="unicode",
        )


# =============================================================================
# Sitemap Builder with Database
# =============================================================================

async def build_sitemap(
    db_session: Any,
    base_url: str,
) -> str:
    """
    Build a complete sitemap from database.
    
    Args:
        db_session: Database session
        base_url: Website base URL
    
    Returns:
        XML sitemap string
    """
    from backend.app import models
    
    generator = SitemapGenerator(base_url)
    
    # Add static pages
    generator.add_static_pages()
    
    # Add animals
    animals = (
        db_session.query(models.Animal)
        .filter(models.Animal.is_adopted == False)
        .order_by(models.Animal.intake_date)
        .limit(10000)
        .all()
    )
    generator.add_animals(animals)
    
    # Add shelters
    shelters = db_session.query(models.Shelter).all()
    generator.add_shelters(shelters)
    
    return generator.generate_xml()


# =============================================================================
# Robots.txt Generator
# =============================================================================

def generate_robots_txt(
    base_url: str,
    sitemap_path: str = "/sitemap.xml",
    disallow_paths: list[str] | None = None,
) -> str:
    """
    Generate robots.txt content.
    
    Args:
        base_url: Website base URL
        sitemap_path: Path to sitemap
        disallow_paths: Paths to disallow
    
    Returns:
        robots.txt content
    """
    lines = [
        "User-agent: *",
    ]
    
    # Add disallow rules
    disallow_paths = disallow_paths or [
        "/api/",
        "/admin/",
        "/_next/",
        "/static/",
    ]
    
    for path in disallow_paths:
        lines.append(f"Disallow: {path}")
    
    # Add allow rules
    lines.extend([
        "",
        "Allow: /",
        "",
        f"Sitemap: {base_url.rstrip('/')}{sitemap_path}",
    ])
    
    return "\n".join(lines)


# =============================================================================
# FastAPI Integration
# =============================================================================

def create_sitemap_routes(app: Any, base_url: str):
    """
    Create sitemap routes for FastAPI app.
    
    Args:
        app: FastAPI application instance
        base_url: Website base URL
    """
    from fastapi import Response
    from backend.app.database import get_db
    
    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap(db=Depends(get_db)):
        xml_content = await build_sitemap(db, base_url)
        return Response(
            content=xml_content,
            media_type="application/xml",
        )
    
    @app.get("/robots.txt", include_in_schema=False)
    async def robots():
        content = generate_robots_txt(base_url)
        return Response(
            content=content,
            media_type="text/plain",
        )
