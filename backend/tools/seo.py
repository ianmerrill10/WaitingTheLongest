"""
Waiting The Longest™ - SEO & Social Meta Generator
====================================================
Generate SEO-optimized meta tags and Open Graph data.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urljoin, quote


@dataclass
class MetaTags:
    """Collection of meta tags for a page."""
    title: str
    description: str
    canonical_url: str
    og_type: str = "website"
    og_image: Optional[str] = None
    og_image_alt: Optional[str] = None
    twitter_card: str = "summary_large_image"
    keywords: Optional[str] = None
    author: str = "Waiting The Longest"
    robots: str = "index, follow"
    
    def to_html(self) -> str:
        """Generate HTML meta tags."""
        tags = [
            f'<title>{self.title}</title>',
            f'<meta name="description" content="{self.description}">',
            f'<link rel="canonical" href="{self.canonical_url}">',
            f'<meta name="robots" content="{self.robots}">',
            f'<meta name="author" content="{self.author}">',
            
            # Open Graph
            f'<meta property="og:title" content="{self.title}">',
            f'<meta property="og:description" content="{self.description}">',
            f'<meta property="og:type" content="{self.og_type}">',
            f'<meta property="og:url" content="{self.canonical_url}">',
            
            # Twitter
            f'<meta name="twitter:card" content="{self.twitter_card}">',
            f'<meta name="twitter:title" content="{self.title}">',
            f'<meta name="twitter:description" content="{self.description}">',
        ]
        
        if self.og_image:
            tags.extend([
                f'<meta property="og:image" content="{self.og_image}">',
                f'<meta name="twitter:image" content="{self.og_image}">',
            ])
            if self.og_image_alt:
                tags.append(f'<meta property="og:image:alt" content="{self.og_image_alt}">')
        
        if self.keywords:
            tags.append(f'<meta name="keywords" content="{self.keywords}">')
        
        return "\n".join(tags)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON responses."""
        return {
            "title": self.title,
            "description": self.description,
            "canonical_url": self.canonical_url,
            "og_type": self.og_type,
            "og_image": self.og_image,
            "og_image_alt": self.og_image_alt,
            "twitter_card": self.twitter_card,
            "keywords": self.keywords,
        }


class SEOGenerator:
    """
    Generate SEO metadata for various pages.
    
    Provides optimized titles, descriptions, and Open Graph data
    for homepage, animal pages, shelter pages, and more.
    """
    
    BASE_URL = "https://waitingthelongest.com"
    SITE_NAME = "Waiting The Longest™"
    DEFAULT_IMAGE = "https://waitingthelongest.com/images/og-default.jpg"
    
    def __init__(self, base_url: Optional[str] = None):
        if base_url:
            self.BASE_URL = base_url.rstrip("/")
    
    def homepage(self) -> MetaTags:
        """Generate meta tags for homepage."""
        return MetaTags(
            title="Waiting The Longest™ | Help Shelter Animals Find Homes",
            description="Discover shelter animals who have been waiting the longest for adoption. Give a long-term shelter pet the forever home they deserve.",
            canonical_url=self.BASE_URL,
            og_image=self.DEFAULT_IMAGE,
            og_image_alt="Shelter animals waiting for adoption",
            keywords="shelter animals, pet adoption, rescue dogs, rescue cats, long-term shelter pets, adopt don't shop",
        )
    
    def animal_page(
        self,
        animal_id: int,
        name: str,
        species: str,
        breed: str,
        days_waiting: int,
        shelter_name: str,
        shelter_city: str,
        shelter_state: str,
        photo_url: Optional[str] = None,
    ) -> MetaTags:
        """Generate meta tags for an animal detail page."""
        title = f"{name} - {breed} for Adoption | {days_waiting} Days Waiting"
        
        description = (
            f"Meet {name}, a {breed.lower()} waiting {days_waiting} days for a forever home at "
            f"{shelter_name} in {shelter_city}, {shelter_state}. Could you be their perfect match?"
        )
        
        return MetaTags(
            title=title,
            description=description[:160],  # Meta description limit
            canonical_url=f"{self.BASE_URL}/animal/{animal_id}",
            og_type="article",
            og_image=photo_url or self.DEFAULT_IMAGE,
            og_image_alt=f"Photo of {name}, a {breed.lower()} available for adoption",
            keywords=f"{breed.lower()}, {species.lower()} adoption, {shelter_city} shelter, rescue {species.lower()}",
        )
    
    def shelter_page(
        self,
        shelter_id: int,
        name: str,
        city: str,
        state: str,
        animal_count: int,
    ) -> MetaTags:
        """Generate meta tags for a shelter page."""
        title = f"{name} - {city}, {state} | {animal_count} Pets for Adoption"
        
        description = (
            f"View {animal_count} adoptable pets at {name} in {city}, {state}. "
            f"Find your perfect companion and give a shelter pet a loving home."
        )
        
        return MetaTags(
            title=title,
            description=description[:160],
            canonical_url=f"{self.BASE_URL}/shelter/{shelter_id}",
            og_type="organization",
            og_image=self.DEFAULT_IMAGE,
            keywords=f"{city} animal shelter, {state} pet adoption, {name} adoptable pets",
        )
    
    def search_results(
        self,
        species: Optional[str] = None,
        state: Optional[str] = None,
        breed: Optional[str] = None,
        result_count: int = 0,
    ) -> MetaTags:
        """Generate meta tags for search results pages."""
        parts = []
        if species:
            parts.append(f"{species.title()}s")
        else:
            parts.append("Pets")
        
        if breed:
            parts = [f"{breed} {parts[0]}"]
        
        if state:
            parts.append(f"in {state}")
        
        parts.append("for Adoption")
        
        title = " ".join(parts) + f" | {result_count} Results"
        
        description = (
            f"Browse {result_count} adoptable {species.lower() + 's' if species else 'pets'} "
            f"{'in ' + state if state else 'near you'}. Find your perfect companion today."
        )
        
        # Build search URL
        params = []
        if species:
            params.append(f"species={quote(species)}")
        if state:
            params.append(f"state={quote(state)}")
        if breed:
            params.append(f"breed={quote(breed)}")
        
        search_url = f"{self.BASE_URL}/search"
        if params:
            search_url += "?" + "&".join(params)
        
        return MetaTags(
            title=title,
            description=description[:160],
            canonical_url=search_url,
            og_image=self.DEFAULT_IMAGE,
            keywords=f"{species or 'pet'} adoption, {state or 'local'} shelter, rescue animals",
            robots="noindex, follow",  # Don't index search results
        )
    
    def success_stories(self) -> MetaTags:
        """Generate meta tags for success stories page."""
        return MetaTags(
            title="Adoption Success Stories | Waiting The Longest™",
            description="Read heartwarming stories of shelter animals who found their forever homes after long waits. These happy endings prove every pet deserves a second chance.",
            canonical_url=f"{self.BASE_URL}/success-stories",
            og_image=self.DEFAULT_IMAGE,
            og_image_alt="Happy adopted pets with their new families",
            keywords="pet adoption stories, shelter success, rescue animals, happy endings",
        )
    
    def about(self) -> MetaTags:
        """Generate meta tags for about page."""
        return MetaTags(
            title="About Us | Waiting The Longest™",
            description="Learn about our mission to highlight shelter animals waiting the longest for adoption. Together, we can help every pet find their forever home.",
            canonical_url=f"{self.BASE_URL}/about",
            og_image=self.DEFAULT_IMAGE,
            keywords="animal shelter advocacy, pet adoption platform, rescue animals",
        )


@dataclass
class StructuredData:
    """JSON-LD structured data for SEO."""
    
    @staticmethod
    def organization() -> Dict[str, Any]:
        """Generate Organization schema."""
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Waiting The Longest",
            "url": "https://waitingthelongest.com",
            "logo": "https://waitingthelongest.com/images/logo.png",
            "description": "A platform dedicated to highlighting shelter animals waiting the longest for adoption.",
            "sameAs": [
                "https://twitter.com/waitinglongest",
                "https://instagram.com/waitingthelongest",
                "https://facebook.com/waitingthelongest",
            ],
        }
    
    @staticmethod
    def animal_listing(
        name: str,
        species: str,
        breed: str,
        description: str,
        image_url: Optional[str],
        shelter_name: str,
        shelter_city: str,
        shelter_state: str,
    ) -> Dict[str, Any]:
        """Generate Product schema for an animal listing."""
        return {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "description": description,
            "image": image_url,
            "category": f"{species} - {breed}",
            "brand": {
                "@type": "Organization",
                "name": shelter_name,
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": shelter_city,
                    "addressRegion": shelter_state,
                }
            },
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "description": "Adoption fee may apply. Contact shelter for details.",
            }
        }
    
    @staticmethod
    def breadcrumb(items: list) -> Dict[str, Any]:
        """Generate BreadcrumbList schema."""
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": item["name"],
                    "item": item["url"],
                }
                for i, item in enumerate(items)
            ]
        }
    
    @staticmethod
    def faq(questions: list) -> Dict[str, Any]:
        """Generate FAQPage schema."""
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": q["answer"],
                    }
                }
                for q in questions
            ]
        }
