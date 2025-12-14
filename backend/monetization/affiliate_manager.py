"""
===============================================================================
Waiting The Longest™ - Affiliate Manager
===============================================================================
Purpose: Unified interface for all affiliate programs.
         Aggregates products from Amazon, Chewy, and other affiliates.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
import random

from .amazon_associates import AmazonAssociates, get_amazon_associate
from .chewy import ChewyAffiliate, get_chewy_affiliate

logger = logging.getLogger(__name__)


class AffiliateSource(str, Enum):
    """Supported affiliate programs."""
    AMAZON = "amazon"
    CHEWY = "chewy"


class AffiliateManager:
    """
    Unified affiliate manager for all partner programs.
    
    Aggregates and rotates products from multiple affiliate sources
    to maximize value for users and revenue.
    """
    
    def __init__(
        self,
        amazon: Optional[AmazonAssociates] = None,
        chewy: Optional[ChewyAffiliate] = None
    ):
        """Initialize with affiliate instances."""
        self.amazon = amazon or get_amazon_associate()
        self.chewy = chewy or get_chewy_affiliate()
    
    def get_adoption_supplies(
        self,
        species: str,
        size: Optional[str] = None,
        age_group: Optional[str] = None,
        tracking_id: Optional[str] = None,
        limit: int = 10,
        shuffle: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recommended supplies for pet adoption from all affiliates.
        
        Args:
            species: "dog" or "cat"
            size: "small", "medium", "large"
            age_group: "puppy", "kitten", "adult", "senior"
            tracking_id: Optional tracking ID for attribution
            limit: Maximum number of products
            shuffle: Randomize product order for A/B testing
            
        Returns:
            List of products from all affiliate sources
        """
        all_products = []
        
        # Get Amazon products
        try:
            amazon_products = self.amazon.get_adoption_essentials(
                species=species,
                size=size,
                age_group=age_group,
                tracking_id=tracking_id or "adoption"
            )
            for product in amazon_products:
                product["source"] = AffiliateSource.AMAZON.value
            all_products.extend(amazon_products)
        except Exception as e:
            logger.warning(f"Failed to get Amazon products: {e}")
        
        # Get Chewy products
        try:
            chewy_products = self.chewy.get_new_pet_supplies(
                species=species,
                size=size,
                age_group=age_group,
                tracking_id=tracking_id or "adoption"
            )
            for product in chewy_products:
                product["source"] = AffiliateSource.CHEWY.value
            all_products.extend(chewy_products)
        except Exception as e:
            logger.warning(f"Failed to get Chewy products: {e}")
        
        # Shuffle for fair distribution
        if shuffle:
            random.shuffle(all_products)
        
        return all_products[:limit]
    
    def get_category_products(
        self,
        category: str,
        species: str = "dog",
        tracking_id: Optional[str] = None,
        source: Optional[AffiliateSource] = None
    ) -> List[Dict[str, Any]]:
        """
        Get products from a specific category.
        
        Args:
            category: Category name (e.g., "food", "toys", "beds")
            species: "dog" or "cat"
            tracking_id: Optional tracking ID
            source: Optional specific affiliate source
            
        Returns:
            List of products
        """
        products = []
        category_key = f"{species}_{category}"
        
        # Amazon
        if source is None or source == AffiliateSource.AMAZON:
            try:
                amazon_key = f"{species.upper()}_{category.upper()}"
                if hasattr(self.amazon, 'PRODUCT_CATEGORIES') and amazon_key in self.amazon.PRODUCT_CATEGORIES:
                    products.append({
                        "title": f"{species.title()} {category.title()}",
                        "url": self.amazon.get_search_url(f"{species} {category}", tracking_id),
                        "source": AffiliateSource.AMAZON.value,
                        "category": category
                    })
            except Exception as e:
                logger.warning(f"Amazon category lookup failed: {e}")
        
        # Chewy
        if source is None or source == AffiliateSource.CHEWY:
            try:
                if category_key in self.chewy.CATEGORIES:
                    products.append({
                        "title": f"{species.title()} {category.title()}",
                        "url": self.chewy.category_link(category_key, tracking_id),
                        "source": AffiliateSource.CHEWY.value,
                        "category": category
                    })
            except Exception as e:
                logger.warning(f"Chewy category lookup failed: {e}")
        
        return products
    
    def get_featured_products(
        self,
        tracking_id: Optional[str] = None,
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get featured products for homepage or sidebar.
        
        Args:
            tracking_id: Optional tracking ID
            limit: Maximum number of products
            
        Returns:
            Mixed list of featured products
        """
        featured = []
        
        # Add some from each category
        categories = [
            ("dog", "food"),
            ("cat", "food"),
            ("dog", "toys"),
            ("cat", "toys"),
            ("dog", "beds"),
            ("cat", "treats"),
        ]
        
        for species, category in categories:
            products = self.get_category_products(
                category=category,
                species=species,
                tracking_id=tracking_id or "featured"
            )
            if products:
                # Alternate sources
                featured.append(random.choice(products))
        
        random.shuffle(featured)
        return featured[:limit]
    
    def track_click(
        self,
        source: AffiliateSource,
        product_id: str,
        tracking_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track an affiliate link click.
        
        Args:
            source: Affiliate source
            product_id: Product identifier
            tracking_id: Tracking ID for attribution
            metadata: Additional click metadata
            
        Returns:
            Click tracking confirmation
        """
        # Log the click for analytics
        logger.info(
            "Affiliate click",
            extra={
                "source": source.value,
                "product_id": product_id,
                "tracking_id": tracking_id,
                **(metadata or {})
            }
        )
        
        return {
            "tracked": True,
            "source": source.value,
            "product_id": product_id,
            "tracking_id": tracking_id
        }


# Singleton instance
_manager: Optional[AffiliateManager] = None


def get_affiliate_manager() -> AffiliateManager:
    """Get or create affiliate manager singleton."""
    global _manager
    if _manager is None:
        _manager = AffiliateManager()
    return _manager
