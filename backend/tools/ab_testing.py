"""
Waiting The Longest™ - A/B Testing Framework
==============================================
Simple A/B testing for feature experimentation.
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class VariantType(Enum):
    """Types of test variants."""
    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass
class Experiment:
    """Definition of an A/B test experiment."""
    id: str
    name: str
    description: str
    control_ratio: float = 0.5  # Percentage that sees control (0.0 - 1.0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    enabled: bool = True
    
    def is_active(self) -> bool:
        """Check if experiment is currently active."""
        if not self.enabled:
            return False
        
        now = datetime.utcnow()
        
        if self.start_date and now < self.start_date:
            return False
        
        if self.end_date and now > self.end_date:
            return False
        
        return True


@dataclass
class ExperimentResult:
    """Result of checking experiment variant for a user."""
    experiment_id: str
    variant: VariantType
    is_control: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ABTestManager:
    """
    Manage A/B tests and variant assignment.
    
    Uses consistent hashing so users always see the same variant
    for a given experiment.
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.results: List[Dict[str, Any]] = []
    
    def register_experiment(self, experiment: Experiment) -> None:
        """Register a new experiment."""
        self.experiments[experiment.id] = experiment
    
    def get_variant(
        self,
        experiment_id: str,
        user_id: str,
    ) -> ExperimentResult:
        """
        Get the variant for a user in an experiment.
        
        Uses consistent hashing based on experiment + user ID.
        """
        experiment = self.experiments.get(experiment_id)
        
        if not experiment or not experiment.is_active():
            # Default to control for inactive experiments
            return ExperimentResult(
                experiment_id=experiment_id,
                variant=VariantType.CONTROL,
                is_control=True,
            )
        
        # Generate consistent hash
        hash_input = f"{experiment_id}:{user_id}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        # Convert first 8 hex chars to a float between 0 and 1
        hash_int = int(hash_value[:8], 16)
        ratio = hash_int / 0xFFFFFFFF
        
        # Determine variant
        is_control = ratio < experiment.control_ratio
        variant = VariantType.CONTROL if is_control else VariantType.TREATMENT
        
        result = ExperimentResult(
            experiment_id=experiment_id,
            variant=variant,
            is_control=is_control,
        )
        
        return result
    
    def is_treatment(self, experiment_id: str, user_id: str) -> bool:
        """Check if user should see treatment variant."""
        result = self.get_variant(experiment_id, user_id)
        return not result.is_control
    
    def track_conversion(
        self,
        experiment_id: str,
        user_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track a conversion event for analysis."""
        result = self.get_variant(experiment_id, user_id)
        
        self.results.append({
            "experiment_id": experiment_id,
            "user_id": user_id,
            "variant": result.variant.value,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
    
    def get_experiment_stats(self, experiment_id: str) -> Dict[str, Any]:
        """Get statistics for an experiment."""
        experiment_results = [
            r for r in self.results
            if r["experiment_id"] == experiment_id
        ]
        
        control_events = [r for r in experiment_results if r["variant"] == "control"]
        treatment_events = [r for r in experiment_results if r["variant"] == "treatment"]
        
        return {
            "experiment_id": experiment_id,
            "total_events": len(experiment_results),
            "control": {
                "events": len(control_events),
            },
            "treatment": {
                "events": len(treatment_events),
            },
        }


# =============================================================================
# Pre-defined Experiments
# =============================================================================

EXPERIMENTS: Dict[str, Experiment] = {
    "homepage_cta_color": Experiment(
        id="homepage_cta_color",
        name="Homepage CTA Button Color",
        description="Test purple vs green CTA button on homepage",
        control_ratio=0.5,
    ),
    "animal_card_layout": Experiment(
        id="animal_card_layout",
        name="Animal Card Layout",
        description="Test horizontal vs vertical animal card layout",
        control_ratio=0.5,
    ),
    "days_waiting_emphasis": Experiment(
        id="days_waiting_emphasis",
        name="Days Waiting Display Emphasis",
        description="Test different ways of displaying wait time",
        control_ratio=0.5,
    ),
    "share_button_position": Experiment(
        id="share_button_position",
        name="Share Button Position",
        description="Test share button at top vs bottom of animal card",
        control_ratio=0.5,
    ),
    "newsletter_popup_timing": Experiment(
        id="newsletter_popup_timing",
        name="Newsletter Popup Timing",
        description="Test showing popup after 30s vs 60s",
        control_ratio=0.5,
    ),
}


# =============================================================================
# Global Instance
# =============================================================================

_ab_manager: Optional[ABTestManager] = None


def get_ab_manager() -> ABTestManager:
    """Get the global A/B test manager."""
    global _ab_manager
    
    if _ab_manager is None:
        _ab_manager = ABTestManager()
        for experiment in EXPERIMENTS.values():
            _ab_manager.register_experiment(experiment)
    
    return _ab_manager


def get_variant(experiment_id: str, user_id: str) -> str:
    """Convenience function to get variant string."""
    manager = get_ab_manager()
    result = manager.get_variant(experiment_id, user_id)
    return result.variant.value


def is_treatment(experiment_id: str, user_id: str) -> bool:
    """Convenience function to check if user is in treatment group."""
    manager = get_ab_manager()
    return manager.is_treatment(experiment_id, user_id)
