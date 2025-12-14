"""
Waiting The Longest™ - Search Service
======================================
Full-text search capabilities for animals.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func


@dataclass
class SearchResult:
    """A search result with relevance score."""
    item: Any
    score: float
    highlights: Dict[str, str] = None
    
    def __post_init__(self):
        if self.highlights is None:
            self.highlights = {}


@dataclass
class SearchQuery:
    """A parsed search query."""
    terms: List[str]
    filters: Dict[str, Any]
    sort_by: str = "relevance"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


class SearchService:
    """
    Search service for animal listings.
    
    Provides:
    - Full-text search with relevance ranking
    - Fuzzy matching
    - Faceted filtering
    - Search suggestions
    """
    
    # Fields to search with their weights
    SEARCH_FIELDS = {
        "name": 10.0,
        "breed": 5.0,
        "description": 2.0,
        "species": 3.0,
    }
    
    # Common search synonyms
    SYNONYMS = {
        "dog": ["pup", "puppy", "canine", "doggo", "pupper"],
        "cat": ["kitten", "kitty", "feline"],
        "small": ["tiny", "petite", "mini"],
        "large": ["big", "giant", "xl"],
        "young": ["baby", "juvenile", "puppy", "kitten"],
        "old": ["senior", "elderly", "aged"],
        "friendly": ["social", "affectionate", "loving", "sweet"],
        "calm": ["mellow", "relaxed", "quiet", "gentle"],
        "active": ["energetic", "playful", "hyper"],
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def parse_query(self, query_string: str) -> SearchQuery:
        """Parse a search string into a structured query."""
        terms = []
        filters = {}
        
        # Extract quoted phrases
        phrases = re.findall(r'"([^"]+)"', query_string)
        terms.extend(phrases)
        query_string = re.sub(r'"[^"]+"', '', query_string)
        
        # Extract filter syntax (field:value)
        filter_matches = re.findall(r'(\w+):(\w+)', query_string)
        for field, value in filter_matches:
            filters[field.lower()] = value.lower()
        query_string = re.sub(r'\w+:\w+', '', query_string)
        
        # Remaining words are search terms
        words = query_string.lower().split()
        terms.extend([w.strip() for w in words if w.strip()])
        
        return SearchQuery(terms=terms, filters=filters)
    
    def expand_synonyms(self, terms: List[str]) -> List[str]:
        """Expand search terms with synonyms."""
        expanded = set(terms)
        
        for term in terms:
            term_lower = term.lower()
            
            # Check if term is a synonym target
            for key, synonyms in self.SYNONYMS.items():
                if term_lower == key:
                    expanded.update(synonyms)
                elif term_lower in synonyms:
                    expanded.add(key)
        
        return list(expanded)
    
    def search(
        self,
        query: str,
        species: Optional[str] = None,
        breed: Optional[str] = None,
        state: Optional[str] = None,
        min_days_waiting: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SearchResult], int]:
        """
        Search animals with relevance ranking.
        
        Returns:
            Tuple of (results, total_count)
        """
        from ..app import models
        
        # Parse and expand query
        parsed = self.parse_query(query)
        search_terms = self.expand_synonyms(parsed.terms)
        
        # Build base query
        base_query = self.db.query(models.Animal).filter(
            models.Animal.is_adopted == False
        )
        
        # Apply filters
        if species:
            base_query = base_query.filter(
                func.lower(models.Animal.species) == species.lower()
            )
        
        if breed:
            base_query = base_query.filter(
                func.lower(models.Animal.breed).contains(breed.lower())
            )
        
        if state:
            base_query = base_query.filter(models.Animal.state == state.upper())
        
        if min_days_waiting:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=min_days_waiting)
            base_query = base_query.filter(models.Animal.intake_date <= cutoff)
        
        # Apply search terms
        if search_terms:
            conditions = []
            for term in search_terms:
                term_conditions = []
                for field in ["name", "breed", "description"]:
                    term_conditions.append(
                        func.lower(getattr(models.Animal, field)).contains(term.lower())
                    )
                conditions.append(or_(*term_conditions))
            
            base_query = base_query.filter(or_(*conditions))
        
        # Get total count
        total = base_query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        animals = base_query.offset(offset).limit(page_size).all()
        
        # Calculate relevance scores
        results = []
        for animal in animals:
            score = self._calculate_relevance(animal, search_terms)
            highlights = self._generate_highlights(animal, search_terms)
            results.append(SearchResult(item=animal, score=score, highlights=highlights))
        
        # Sort by relevance
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results, total
    
    def _calculate_relevance(self, animal, terms: List[str]) -> float:
        """Calculate relevance score for an animal."""
        score = 0.0
        
        for term in terms:
            term_lower = term.lower()
            
            # Check each searchable field
            for field, weight in self.SEARCH_FIELDS.items():
                value = getattr(animal, field, "") or ""
                value_lower = value.lower()
                
                # Exact match in field
                if term_lower == value_lower:
                    score += weight * 3
                # Term appears in field
                elif term_lower in value_lower:
                    score += weight
                # Partial match (prefix)
                elif value_lower.startswith(term_lower):
                    score += weight * 0.5
        
        # Boost score for longer-waiting animals
        days_waiting = getattr(animal, "days_waiting", 0)
        if days_waiting > 30:
            score *= 1.1
        if days_waiting > 90:
            score *= 1.2
        if days_waiting > 180:
            score *= 1.3
        
        return score
    
    def _generate_highlights(self, animal, terms: List[str]) -> Dict[str, str]:
        """Generate highlighted snippets for search terms."""
        highlights = {}
        
        for field in ["name", "breed", "description"]:
            value = getattr(animal, field, "") or ""
            if not value:
                continue
            
            highlighted = value
            for term in terms:
                pattern = re.compile(f"({re.escape(term)})", re.IGNORECASE)
                highlighted = pattern.sub(r"<mark>\1</mark>", highlighted)
            
            if highlighted != value:
                # Truncate description to snippet
                if field == "description" and len(highlighted) > 200:
                    # Find first match and show context
                    first_mark = highlighted.find("<mark>")
                    if first_mark > 50:
                        highlighted = "..." + highlighted[first_mark - 50:]
                    if len(highlighted) > 200:
                        highlighted = highlighted[:200] + "..."
                
                highlights[field] = highlighted
        
        return highlights
    
    def get_suggestions(self, partial: str, limit: int = 5) -> List[str]:
        """Get search suggestions for partial input."""
        from ..app import models
        
        suggestions = set()
        partial_lower = partial.lower()
        
        # Suggest from animal names
        names = self.db.query(models.Animal.name).filter(
            func.lower(models.Animal.name).startswith(partial_lower),
            models.Animal.is_adopted == False,
        ).limit(limit).all()
        suggestions.update(name[0] for name in names if name[0])
        
        # Suggest from breeds
        if len(suggestions) < limit:
            breeds = self.db.query(models.Animal.breed).filter(
                func.lower(models.Animal.breed).startswith(partial_lower)
            ).distinct().limit(limit - len(suggestions)).all()
            suggestions.update(breed[0] for breed in breeds if breed[0])
        
        return sorted(list(suggestions))[:limit]
    
    def get_facets(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get available facets for filtering."""
        from ..app import models
        
        facets = {}
        
        # Species facet
        species_counts = self.db.query(
            models.Animal.species,
            func.count(models.Animal.id)
        ).filter(
            models.Animal.is_adopted == False
        ).group_by(models.Animal.species).all()
        
        facets["species"] = [
            {"value": s, "count": c}
            for s, c in species_counts if s
        ]
        
        # State facet
        state_counts = self.db.query(
            models.Animal.state,
            func.count(models.Animal.id)
        ).filter(
            models.Animal.is_adopted == False,
            models.Animal.state.isnot(None)
        ).group_by(models.Animal.state).all()
        
        facets["states"] = [
            {"value": s, "count": c}
            for s, c in state_counts if s
        ]
        
        return facets
