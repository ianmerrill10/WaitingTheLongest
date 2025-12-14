"""
===============================================================================
Waiting The Longest™ - Chewy Affiliate Integration
===============================================================================
Purpose: Chewy pet supplies affiliate integration.
         Generates affiliate links for pet supplies recommendations.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode, quote_plus

logger = logging.getLogger(__name__)


class ChewyAffiliate:
    """
    Chewy affiliate link generator.
    
    Uses Chewy's Impact affiliate program for commission on pet supplies.
    """
    
    # Base URL for Chewy's Impact affiliate tracking
    BASE_URL = "https://www.chewy.com"
    IMPACT_TRACKING_URL = "https://chewy.pxf.io/c/{publisher_id}/{program_id}"
    
    # Default affiliate config
    DEFAULT_PUBLISHER_ID = ""  # Set via environment
    DEFAULT_PROGRAM_ID = ""    # Set via environment
    
    # Product categories
    CATEGORIES = {
        "dog_food": "/b/food-shop-dog-287",
        "cat_food": "/b/food-shop-cat-324",
        "dog_treats": "/b/treats-shop-dog-268",
        "cat_treats": "/b/treats-shop-cat-326",
        "dog_toys": "/b/toys-shop-dog-285",
        "cat_toys": "/b/toys-shop-cat-325",
        "dog_beds": "/b/beds-shop-dog-284",
        "cat_beds": "/b/beds-shop-cat-328",
        "dog_bowls": "/b/bowls-and-feeders-shop-dog-287",
        "cat_bowls": "/b/bowls-and-feeders-shop-cat-324",
        "dog_crates": "/b/crates-shop-dog-284",
        "cat_carriers": "/b/carriers-shop-cat-328",
        "dog_collars": "/b/collars-shop-dog-284",
        "cat_collars": "/b/collars-shop-cat-328",
        "dog_health": "/b/healthcare-shop-dog-268",
        "cat_health": "/b/healthcare-shop-cat-326",
    }
    
    # Brand-specific links for common products
    POPULAR_BRANDS = {
        "blue_buffalo": "/b/blue-buffalo-dog-food-287",
        "purina": "/b/purina-dog-food-287",
        "hills_science_diet": "/b/hills-science-diet-dog-food-287",
        "royal_canin": "/b/royal-canin-dog-food-287",
        "iams": "/b/iams-dog-food-287",
        "wellness": "/b/wellness-dog-food-287",
        "merrick": "/b/merrick-dog-food-287",
        "taste_of_wild": "/b/taste-of-the-wild-dog-food-287",
    }
    
    def __init__(
        self,
        publisher_id: Optional[str] = None,
        program_id: Optional[str] = None
    ):
        """Initialize Chewy affiliate with credentials."""
        self.publisher_id = publisher_id or self.DEFAULT_PUBLISHER_ID
        self.program_id = program_id or self.DEFAULT_PROGRAM_ID
    
    def generate_link(
        self,
        path: str = "/",
        tracking_id: Optional[str] = None
    ) -> str:
        """
        Generate a Chewy affiliate link.
        
        Args:
            path: Chewy URL path (e.g., "/b/dog-food-287")
            tracking_id: Optional sub-tracking ID
            
        Returns:
            Affiliate link URL
        """
        if not self.publisher_id or not self.program_id:
            # Fallback to direct link if no affiliate config
            return f"{self.BASE_URL}{path}"
        
        # Build Impact tracking URL
        params = {
            "u": f"{self.BASE_URL}{path}"
        }
        if tracking_id:
            params["subId1"] = tracking_id
        
        return f"{self.IMPACT_TRACKING_URL.format(publisher_id=self.publisher_id, program_id=self.program_id)}?{urlencode(params)}"
    
    def search_link(
        self,
        query: str,
        species: str = "dog",
        tracking_id: Optional[str] = None
    ) -> str:
        """
        Generate a search affiliate link.
        
        Args:
            query: Search query
            species: "dog" or "cat"
            tracking_id: Optional sub-tracking ID
            
        Returns:
            Affiliate search link
        """
        path = f"/s?query={quote_plus(query)}&dept={species}"
        return self.generate_link(path, tracking_id)
    
    def category_link(
        self,
        category: str,
        tracking_id: Optional[str] = None
    ) -> str:
        """
        Generate a category affiliate link.
        
        Args:
            category: Category key from CATEGORIES
            tracking_id: Optional sub-tracking ID
            
        Returns:
            Affiliate category link
        """
        path = self.CATEGORIES.get(category, "/")
        return self.generate_link(path, tracking_id)
    
    def get_new_pet_supplies(
        self,
        species: str,
        size: Optional[str] = None,
        age_group: Optional[str] = None,
        tracking_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get recommended supplies for a new pet adoption.
        
        Args:
            species: "dog" or "cat"
            size: "small", "medium", "large" (for dogs)
            age_group: "puppy", "kitten", "adult", "senior"
            tracking_id: Optional sub-tracking ID
            
        Returns:
            List of recommended products with affiliate links
        """
        recommendations = []
        species_lower = species.lower()
        
        if species_lower not in ["dog", "cat"]:
            species_lower = "dog"  # Default
        
        # Essential categories
        essentials = [
            (f"{species_lower}_food", "Premium Food", "Start your new pet with quality nutrition"),
            (f"{species_lower}_bowls", "Food & Water Bowls", "Essential feeding supplies"),
            (f"{species_lower}_beds", "Cozy Bed", "Give your pet a comfortable place to rest"),
            (f"{species_lower}_toys", "Toys & Enrichment", "Keep your pet entertained"),
            (f"{species_lower}_treats", "Training Treats", "Perfect for positive reinforcement"),
            (f"{species_lower}_health", "Health Supplies", "First aid and health essentials"),
        ]
        
        if species_lower == "dog":
            essentials.extend([
                ("dog_crates", "Crate & Carrier", "Safe travel and training"),
                ("dog_collars", "Collar & Leash", "For walks and ID tags"),
            ])
        else:
            essentials.extend([
                ("cat_carriers", "Carrier", "Safe travel to vet"),
                ("cat_collars", "Collar & ID Tag", "Keep your cat identifiable"),
            ])
        
        for category_key, title, description in essentials:
            recommendations.append({
                "title": title,
                "description": description,
                "url": self.category_link(category_key, tracking_id),
                "category": category_key,
                "source": "chewy"
            })
        
        return recommendations
    
    def get_size_specific_recommendations(
        self,
        size: str,
        tracking_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get size-specific product recommendations.
        
        Args:
            size: "small", "medium", "large", "extra large"
            tracking_id: Optional sub-tracking ID
            
        Returns:
            List of size-appropriate products
        """
        size_lower = size.lower().replace(" ", "")
        
        size_queries = {
            "small": ["small breed dog food", "small dog toys", "small dog bed"],
            "medium": ["medium breed dog food", "medium dog toys", "medium dog bed"],
            "large": ["large breed dog food", "large dog toys", "large dog bed"],
            "extralarge": ["giant breed dog food", "xlarge dog toys", "extra large dog bed"],
        }
        
        queries = size_queries.get(size_lower, size_queries["medium"])
        
        return [
            {
                "title": query.title(),
                "url": self.search_link(query, "dog", tracking_id),
                "source": "chewy"
            }
            for query in queries
        ]


# Singleton instance
_chewy: Optional[ChewyAffiliate] = None


def get_chewy_affiliate(
    publisher_id: Optional[str] = None,
    program_id: Optional[str] = None
) -> ChewyAffiliate:
    """Get or create Chewy affiliate singleton."""
    global _chewy
    if _chewy is None:
        import os
        _chewy = ChewyAffiliate(
            publisher_id=publisher_id or os.environ.get("CHEWY_PUBLISHER_ID"),
            program_id=program_id or os.environ.get("CHEWY_PROGRAM_ID")
        )
    return _chewy
