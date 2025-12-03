"""
Waiting The Longest™ - Monetization Modules
===========================================
Affiliate marketing and revenue generation.

Amazon Associate ID: waitingthelon-20
"""

# Lazy import to avoid circular dependencies
__all__ = ["AmazonAssociates", "track_affiliate_click"]

def __getattr__(name):
    if name in __all__:
        from .amazon_associates import AmazonAssociates, track_affiliate_click
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
