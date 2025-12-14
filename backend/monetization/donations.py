"""
Waiting The Longest™ - Donation Integration
=============================================
Support donation processing for shelters.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class DonationType(Enum):
    """Types of donations."""
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    SPONSOR = "sponsor"  # Sponsor a specific animal


class PaymentProvider(Enum):
    """Supported payment providers."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    VENMO = "venmo"
    DIRECT = "direct"  # Direct to shelter


@dataclass
class DonationTarget:
    """A donation target (shelter or animal)."""
    id: str
    type: str  # "shelter" or "animal"
    name: str
    description: Optional[str] = None
    goal_amount: Optional[float] = None
    raised_amount: float = 0.0
    
    @property
    def progress_percent(self) -> float:
        """Get progress towards goal."""
        if not self.goal_amount or self.goal_amount <= 0:
            return 0.0
        return min(100.0, (self.raised_amount / self.goal_amount) * 100)


@dataclass
class Donation:
    """A donation record."""
    id: str
    amount: float
    currency: str
    type: DonationType
    target: DonationTarget
    donor_email: Optional[str] = None
    donor_name: Optional[str] = None
    is_anonymous: bool = False
    message: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class DonationManager:
    """
    Manage donation flows and integrations.
    
    Supports multiple payment providers and donation types.
    """
    
    # Suggested donation amounts
    SUGGESTED_AMOUNTS = [10, 25, 50, 100, 250]
    
    # Animal sponsorship amounts (monthly)
    SPONSORSHIP_TIERS = {
        "bronze": {"amount": 15, "name": "Bronze Sponsor", "perks": ["Updates", "Certificate"]},
        "silver": {"amount": 30, "name": "Silver Sponsor", "perks": ["Updates", "Certificate", "Photo"]},
        "gold": {"amount": 50, "name": "Gold Sponsor", "perks": ["Updates", "Certificate", "Photo", "Visit"]},
    }
    
    def __init__(self):
        self.donations: List[Donation] = []
        self._stripe_configured = False
        self._paypal_configured = False
    
    def configure_stripe(self, api_key: str) -> None:
        """Configure Stripe integration."""
        # In production, this would set up the Stripe client
        self._stripe_configured = True
        logger.info("Stripe donation integration configured")
    
    def configure_paypal(self, client_id: str, client_secret: str) -> None:
        """Configure PayPal integration."""
        # In production, this would set up the PayPal client
        self._paypal_configured = True
        logger.info("PayPal donation integration configured")
    
    def create_donation_session(
        self,
        amount: float,
        currency: str,
        target: DonationTarget,
        donation_type: DonationType,
        provider: PaymentProvider,
        donor_email: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a donation checkout session.
        
        Returns provider-specific session data.
        """
        if provider == PaymentProvider.STRIPE:
            return self._create_stripe_session(
                amount, currency, target, donation_type, donor_email, success_url, cancel_url
            )
        elif provider == PaymentProvider.PAYPAL:
            return self._create_paypal_order(
                amount, currency, target, donation_type
            )
        elif provider == PaymentProvider.DIRECT:
            return self._get_direct_donation_info(target)
        else:
            raise ValueError(f"Unsupported payment provider: {provider}")
    
    def _create_stripe_session(
        self,
        amount: float,
        currency: str,
        target: DonationTarget,
        donation_type: DonationType,
        donor_email: Optional[str],
        success_url: Optional[str],
        cancel_url: Optional[str],
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session."""
        # In production, this would use stripe.checkout.Session.create()
        session_id = f"cs_{target.type}_{target.id}_{int(amount * 100)}"
        
        return {
            "provider": "stripe",
            "session_id": session_id,
            "checkout_url": f"https://checkout.stripe.com/pay/{session_id}",
            "amount": amount,
            "currency": currency,
            "mode": "subscription" if donation_type == DonationType.MONTHLY else "payment",
        }
    
    def _create_paypal_order(
        self,
        amount: float,
        currency: str,
        target: DonationTarget,
        donation_type: DonationType,
    ) -> Dict[str, Any]:
        """Create a PayPal order."""
        # In production, this would use PayPal Orders API
        order_id = f"PP_{target.type}_{target.id}_{int(amount * 100)}"
        
        return {
            "provider": "paypal",
            "order_id": order_id,
            "approval_url": f"https://www.paypal.com/checkoutnow?token={order_id}",
            "amount": amount,
            "currency": currency,
        }
    
    def _get_direct_donation_info(self, target: DonationTarget) -> Dict[str, Any]:
        """Get direct donation information for a shelter."""
        return {
            "provider": "direct",
            "target": target.name,
            "message": f"To donate directly to {target.name}, please visit their website or contact them directly.",
            "website_suggestion": f"https://www.google.com/search?q={target.name.replace(' ', '+')}+donations",
        }
    
    def record_donation(self, donation: Donation) -> None:
        """Record a completed donation."""
        self.donations.append(donation)
        donation.target.raised_amount += donation.amount
        
        logger.info(
            f"Donation recorded: ${donation.amount} to {donation.target.name}",
            extra={
                "amount": donation.amount,
                "target_type": donation.target.type,
                "target_id": donation.target.id,
                "donation_type": donation.type.value,
            }
        )
    
    def get_donation_stats(self) -> Dict[str, Any]:
        """Get aggregate donation statistics."""
        total_raised = sum(d.amount for d in self.donations)
        donation_count = len(self.donations)
        
        by_type = {}
        for dtype in DonationType:
            type_donations = [d for d in self.donations if d.type == dtype]
            by_type[dtype.value] = {
                "count": len(type_donations),
                "total": sum(d.amount for d in type_donations),
            }
        
        return {
            "total_raised": total_raised,
            "donation_count": donation_count,
            "average_donation": total_raised / donation_count if donation_count > 0 else 0,
            "by_type": by_type,
        }
    
    def get_sponsorship_options(self, animal_id: int, animal_name: str) -> Dict[str, Any]:
        """Get sponsorship options for an animal."""
        return {
            "animal_id": animal_id,
            "animal_name": animal_name,
            "tiers": [
                {
                    "id": tier_id,
                    "name": tier["name"],
                    "amount": tier["amount"],
                    "perks": tier["perks"],
                }
                for tier_id, tier in self.SPONSORSHIP_TIERS.items()
            ],
            "description": f"Sponsor {animal_name}'s care while they wait for their forever home!",
        }
    
    def generate_donation_button_html(
        self,
        target: DonationTarget,
        amount: Optional[float] = None,
        style: str = "primary",
    ) -> str:
        """Generate HTML for a donation button."""
        amount_str = f"${amount:.0f}" if amount else "Donate"
        
        return f"""
        <button
            class="donate-btn donate-btn-{style}"
            data-target-type="{target.type}"
            data-target-id="{target.id}"
            data-amount="{amount or ''}"
            onclick="openDonationModal('{target.type}', '{target.id}')"
        >
            💝 {amount_str} to {target.name}
        </button>
        """


# =============================================================================
# Donation Widget Generator
# =============================================================================

class DonationWidget:
    """Generate embeddable donation widgets."""
    
    @staticmethod
    def generate_shelter_widget(
        shelter_name: str,
        shelter_id: str,
        theme: str = "light",
    ) -> str:
        """Generate an embeddable shelter donation widget."""
        return f"""
        <div class="wtl-donation-widget" data-theme="{theme}">
            <div class="wtl-widget-header">
                <h3>Support {shelter_name}</h3>
                <p>Help animals find their forever homes</p>
            </div>
            <div class="wtl-widget-amounts">
                <button class="wtl-amount" data-amount="10">$10</button>
                <button class="wtl-amount" data-amount="25">$25</button>
                <button class="wtl-amount" data-amount="50">$50</button>
                <button class="wtl-amount" data-amount="100">$100</button>
            </div>
            <input type="number" class="wtl-custom-amount" placeholder="Custom amount">
            <button class="wtl-donate-btn" onclick="wtlDonate('{shelter_id}')">
                Donate Now
            </button>
            <p class="wtl-powered-by">
                Powered by <a href="https://waitingthelongest.com">Waiting The Longest™</a>
            </p>
        </div>
        """
    
    @staticmethod
    def generate_progress_bar(
        target: DonationTarget,
    ) -> str:
        """Generate a donation progress bar."""
        progress = target.progress_percent
        
        return f"""
        <div class="wtl-progress-container">
            <div class="wtl-progress-bar" style="width: {progress}%"></div>
            <div class="wtl-progress-stats">
                <span class="wtl-raised">${target.raised_amount:,.0f} raised</span>
                <span class="wtl-goal">of ${target.goal_amount:,.0f} goal</span>
            </div>
        </div>
        """
