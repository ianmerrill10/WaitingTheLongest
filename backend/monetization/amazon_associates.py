"""
===============================================================================
Waiting The Longest™ - Amazon Associates Monetization
===============================================================================
Purpose: Amazon Associates affiliate link generation and product 
         recommendations. Handles click tracking for revenue attribution.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: pydantic, urllib
Related Files: main.py, models.py, config.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Your Associate ID: waitingthelon-20

CRITICAL: You need 3 qualified sales within 180 days of account activation
to keep your Associates account active!

Commission Rates (Pet Products):
- Pet Products: 2-8%
- Pet Food: 4%
- Toys: 3%
- Luxury Beauty (pet grooming): 10%
===============================================================================
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
from urllib.parse import urlencode
import hashlib
from datetime import datetime, timezone

try:
    from app.config import settings
except ImportError:
    from ..app.config import settings


class AffiliateProduct(BaseModel):
    """Product recommendation with affiliate tracking"""
    product_id: str
    name: str
    category: str  # "food", "toys", "beds", "training", "grooming"
    pet_type: str  # "dog", "cat", "both"
    pet_size: Optional[str] = None  # "small", "medium", "large"
    pet_age: Optional[str] = None  # "puppy", "adult", "senior"
    amazon_asin: str
    price_range: str  # "$", "$$", "$$$"
    priority: int = 5  # 1-10, higher = show first
    description: Optional[str] = None
    image_url: Optional[str] = None


class AmazonAssociates:
    """
    Amazon Associates affiliate link manager.

    Your Associate ID: waitingthelon-20
    """

    ASSOCIATE_ID = settings.AMAZON_ASSOCIATE_ID or "waitingthelon-20"

    # Product catalog - curated recommendations
    PRODUCT_CATALOG: List[AffiliateProduct] = [
        # Dog Essentials - Puppies
        AffiliateProduct(
            product_id="dog-crate-midwest",
            name="MidWest Homes Dog Crate",
            category="housing",
            pet_type="dog",
            pet_age="puppy",
            amazon_asin="B000OXAEIG",
            price_range="$$",
            priority=9,
            description="Essential for house training - folds flat for storage"
        ),
        AffiliateProduct(
            product_id="puppy-food-blue",
            name="Blue Buffalo Puppy Food",
            category="food",
            pet_type="dog",
            pet_age="puppy",
            amazon_asin="B00HFVHG8M",
            price_range="$$",
            priority=9,
            description="High-quality nutrition for growing puppies"
        ),
        AffiliateProduct(
            product_id="kong-puppy",
            name="KONG Puppy Toy",
            category="toys",
            pet_type="dog",
            pet_age="puppy",
            amazon_asin="B0002AR0I8",
            price_range="$",
            priority=8,
            description="Perfect for teething puppies - stuff with treats"
        ),
        AffiliateProduct(
            product_id="puppy-pads",
            name="Amazon Basics Puppy Pads",
            category="training",
            pet_type="dog",
            pet_age="puppy",
            amazon_asin="B00MW8G62E",
            price_range="$",
            priority=8,
            description="Essential for potty training"
        ),

        # Dog Essentials - Adults
        AffiliateProduct(
            product_id="dog-bed-furhaven",
            name="Furhaven Orthopedic Dog Bed",
            category="beds",
            pet_type="dog",
            pet_size="large",
            amazon_asin="B074MRDQMR",
            price_range="$$",
            priority=8,
            description="Memory foam comfort for large dogs"
        ),
        AffiliateProduct(
            product_id="dog-food-taste",
            name="Taste of the Wild Dog Food",
            category="food",
            pet_type="dog",
            amazon_asin="B001HYB2TI",
            price_range="$$",
            priority=7,
            description="Grain-free premium nutrition"
        ),
        AffiliateProduct(
            product_id="dog-leash-flexi",
            name="Flexi Retractable Dog Leash",
            category="walking",
            pet_type="dog",
            amazon_asin="B00BEFKTBY",
            price_range="$$",
            priority=7,
            description="Freedom for walks with safety control"
        ),

        # Cat Essentials
        AffiliateProduct(
            product_id="cat-litter-box",
            name="Nature's Miracle Litter Box",
            category="housing",
            pet_type="cat",
            amazon_asin="B000633Y1O",
            price_range="$",
            priority=9,
            description="High-sided to prevent scatter"
        ),
        AffiliateProduct(
            product_id="cat-food-hills",
            name="Hill's Science Diet Cat Food",
            category="food",
            pet_type="cat",
            amazon_asin="B074WG2S6Z",
            price_range="$$",
            priority=8,
            description="Vet-recommended nutrition"
        ),
        AffiliateProduct(
            product_id="cat-tree",
            name="Go Pet Club Cat Tree",
            category="furniture",
            pet_type="cat",
            amazon_asin="B003WGGWQA",
            price_range="$$",
            priority=7,
            description="Multi-level climbing and scratching"
        ),
        AffiliateProduct(
            product_id="cat-carrier",
            name="Sherpa Original Deluxe Pet Carrier",
            category="transport",
            pet_type="cat",
            amazon_asin="B0002YFPA2",
            price_range="$$",
            priority=8,
            description="Airline approved, essential for vet visits"
        ),

        # Universal
        AffiliateProduct(
            product_id="pet-water-fountain",
            name="Catit Flower Water Fountain",
            category="feeding",
            pet_type="both",
            amazon_asin="B0146QXOB0",
            price_range="$",
            priority=6,
            description="Encourages hydration with flowing water"
        ),
        AffiliateProduct(
            product_id="furminator",
            name="FURminator deShedding Tool",
            category="grooming",
            pet_type="both",
            amazon_asin="B0040QW35A",
            price_range="$$",
            priority=7,
            description="Reduces shedding up to 90%"
        ),
    ]

    @classmethod
    def create_affiliate_link(cls, asin: str, campaign: str = "website") -> str:
        """
        Generate a properly tracked Amazon affiliate link.

        Args:
            asin: Amazon Standard Identification Number
            campaign: Campaign tag for tracking (e.g., "homepage", "petdetail")

        Returns:
            Full affiliate URL
        """
        base_url = f"https://www.amazon.com/dp/{asin}"
        params = {
            "tag": cls.ASSOCIATE_ID,
            "linkCode": "as2",
            "camp": "1789",
            "creative": "9325",
        }

        return f"{base_url}?{urlencode(params)}"

    @classmethod
    def get_recommendations(
        cls,
        pet_type: str,
        pet_age: Optional[str] = None,
        pet_size: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get personalized product recommendations.

        Args:
            pet_type: "dog", "cat", or "both"
            pet_age: "puppy", "adult", "senior"
            pet_size: "small", "medium", "large"
            category: Specific category filter
            limit: Maximum number of recommendations

        Returns:
            List of products with affiliate links
        """
        # Filter products
        filtered = []
        for product in cls.PRODUCT_CATALOG:
            # Match pet type
            if product.pet_type not in [pet_type, "both"]:
                continue

            # Match age if specified
            if pet_age and product.pet_age and product.pet_age != pet_age:
                continue

            # Match size if specified
            if pet_size and product.pet_size and product.pet_size != pet_size:
                continue

            # Match category if specified
            if category and product.category != category:
                continue

            filtered.append(product)

        # Sort by priority and limit
        filtered.sort(key=lambda x: x.priority, reverse=True)
        filtered = filtered[:limit]

        # Add affiliate links
        results = []
        for product in filtered:
            results.append({
                "name": product.name,
                "category": product.category,
                "description": product.description,
                "price_range": product.price_range,
                "affiliate_url": cls.create_affiliate_link(
                    product.amazon_asin,
                    campaign=f"rec_{pet_type}"
                ),
                "asin": product.amazon_asin
            })

        return results

    @classmethod
    def get_new_pet_essentials(cls, pet_type: str, pet_age: str = "adult") -> Dict:
        """
        Get essential products for newly adopted pets.

        This is a high-converting placement - new adopters need supplies!
        """
        essentials = cls.get_recommendations(
            pet_type=pet_type,
            pet_age=pet_age,
            limit=10
        )

        return {
            "title": f"Essential Supplies for Your New {pet_type.capitalize()}",
            "message": "These are the must-haves for your newly adopted pet!",
            "products": essentials,
            "disclosure": "As an Amazon Associate, Waiting The Longest earns from qualifying purchases."
        }

    @classmethod
    def generate_html_widget(cls, products: List[Dict], title: str = "Recommended Products") -> str:
        """
        Generate HTML widget for embedding product recommendations.
        """
        html = f'''
<div class="wtl-affiliate-widget">
    <h3>{title}</h3>
    <p class="affiliate-disclosure">As an Amazon Associate, we earn from qualifying purchases.</p>
    <div class="product-grid">
'''

        for product in products:
            html += f'''
        <div class="product-card">
            <a href="{product['affiliate_url']}" target="_blank" rel="noopener sponsored">
                <div class="product-name">{product['name']}</div>
                <div class="product-price">{product['price_range']}</div>
                <div class="product-desc">{product.get('description', '')}</div>
                <button class="shop-button">Shop on Amazon</button>
            </a>
        </div>
'''

        html += '''
    </div>
</div>
'''
        return html


# =============================================================================
# Affiliate Click Tracking
# =============================================================================

def track_affiliate_click(
    db,
    product_id: str,
    program: str,
    source_page: Optional[str] = None,
    animal_id: Optional[int] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """
    Track an affiliate link click for analytics.

    We hash IP addresses for privacy.
    """
    try:
        from app.models import AffiliateClick
    except ImportError:
        from ..app.models import AffiliateClick

    ip_hash = None
    if ip_address:
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]

    click = AffiliateClick(
        product_id=product_id,
        affiliate_program=program,
        source_page=source_page,
        animal_id=animal_id,
        session_id=session_id,
        ip_hash=ip_hash,
        clicked_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )

    db.add(click)
    db.commit()

    return click.id
