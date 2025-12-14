"""
Waiting The Longest™ - Geocoding Utilities
===========================================
Convert addresses to coordinates for map features.
"""

import re
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Represents a geographic location."""
    latitude: float
    longitude: float
    formatted_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = "US"
    
    @property
    def coordinates(self) -> Tuple[float, float]:
        """Return (lat, lng) tuple."""
        return (self.latitude, self.longitude)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "formatted_address": self.formatted_address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
        }
    
    def distance_to(self, other: "GeoLocation") -> float:
        """Calculate distance in miles to another location using Haversine formula."""
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other.latitude), radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        
        # Earth radius in miles
        r = 3956
        
        return c * r


# US State coordinates (approximate centers)
US_STATE_COORDINATES: Dict[str, Tuple[float, float]] = {
    "AL": (32.806671, -86.791130),
    "AK": (61.370716, -152.404419),
    "AZ": (33.729759, -111.431221),
    "AR": (34.969704, -92.373123),
    "CA": (36.116203, -119.681564),
    "CO": (39.059811, -105.311104),
    "CT": (41.597782, -72.755371),
    "DE": (39.318523, -75.507141),
    "FL": (27.766279, -81.686783),
    "GA": (33.040619, -83.643074),
    "HI": (21.094318, -157.498337),
    "ID": (44.240459, -114.478828),
    "IL": (40.349457, -88.986137),
    "IN": (39.849426, -86.258278),
    "IA": (42.011539, -93.210526),
    "KS": (38.526600, -96.726486),
    "KY": (37.668140, -84.670067),
    "LA": (31.169546, -91.867805),
    "ME": (44.693947, -69.381927),
    "MD": (39.063946, -76.802101),
    "MA": (42.230171, -71.530106),
    "MI": (43.326618, -84.536095),
    "MN": (45.694454, -93.900192),
    "MS": (32.741646, -89.678696),
    "MO": (38.456085, -92.288368),
    "MT": (46.921925, -110.454353),
    "NE": (41.125370, -98.268082),
    "NV": (38.313515, -117.055374),
    "NH": (43.452492, -71.563896),
    "NJ": (40.298904, -74.521011),
    "NM": (34.840515, -106.248482),
    "NY": (42.165726, -74.948051),
    "NC": (35.630066, -79.806419),
    "ND": (47.528912, -99.784012),
    "OH": (40.388783, -82.764915),
    "OK": (35.565342, -96.928917),
    "OR": (44.572021, -122.070938),
    "PA": (40.590752, -77.209755),
    "RI": (41.680893, -71.511780),
    "SC": (33.856892, -80.945007),
    "SD": (44.299782, -99.438828),
    "TN": (35.747845, -86.692345),
    "TX": (31.054487, -97.563461),
    "UT": (40.150032, -111.862434),
    "VT": (44.045876, -72.710686),
    "VA": (37.769337, -78.169968),
    "WA": (47.400902, -121.490494),
    "WV": (38.491226, -80.954456),
    "WI": (44.268543, -89.616508),
    "WY": (42.755966, -107.302490),
    "DC": (38.897438, -77.026817),
}

# Major US city coordinates
US_CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "New York, NY": (40.7128, -74.0060),
    "Los Angeles, CA": (34.0522, -118.2437),
    "Chicago, IL": (41.8781, -87.6298),
    "Houston, TX": (29.7604, -95.3698),
    "Phoenix, AZ": (33.4484, -112.0740),
    "Philadelphia, PA": (39.9526, -75.1652),
    "San Antonio, TX": (29.4241, -98.4936),
    "San Diego, CA": (32.7157, -117.1611),
    "Dallas, TX": (32.7767, -96.7970),
    "San Jose, CA": (37.3382, -121.8863),
    "Austin, TX": (30.2672, -97.7431),
    "Jacksonville, FL": (30.3322, -81.6557),
    "Fort Worth, TX": (32.7555, -97.3308),
    "Columbus, OH": (39.9612, -82.9988),
    "Charlotte, NC": (35.2271, -80.8431),
    "San Francisco, CA": (37.7749, -122.4194),
    "Indianapolis, IN": (39.7684, -86.1581),
    "Seattle, WA": (47.6062, -122.3321),
    "Denver, CO": (39.7392, -104.9903),
    "Washington, DC": (38.9072, -77.0369),
    "Boston, MA": (42.3601, -71.0589),
    "Nashville, TN": (36.1627, -86.7816),
    "Detroit, MI": (42.3314, -83.0458),
    "Portland, OR": (45.5051, -122.6750),
    "Las Vegas, NV": (36.1699, -115.1398),
    "Memphis, TN": (35.1495, -90.0490),
    "Louisville, KY": (38.2527, -85.7585),
    "Baltimore, MD": (39.2904, -76.6122),
    "Milwaukee, WI": (43.0389, -87.9065),
    "Albuquerque, NM": (35.0844, -106.6504),
    "Tucson, AZ": (32.2226, -110.9747),
    "Fresno, CA": (36.7378, -119.7871),
    "Atlanta, GA": (33.7490, -84.3880),
    "Miami, FL": (25.7617, -80.1918),
    "Orlando, FL": (28.5383, -81.3792),
    "Tampa, FL": (27.9506, -82.4572),
    "Salt Lake City, UT": (40.7608, -111.8910),
    "Kanab, UT": (37.0475, -112.5263),  # Best Friends Animal Sanctuary
}


class Geocoder:
    """
    Geocoding utilities for shelter and adopter locations.
    
    Uses a combination of:
    - Local lookup tables for known cities
    - State centroids for fallback
    - Optional external API for precise geocoding
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize geocoder.
        
        Args:
            api_key: Optional API key for external geocoding service
        """
        self.api_key = api_key
        self._cache: Dict[str, GeoLocation] = {}
    
    def geocode_sync(
        self,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
    ) -> Optional[GeoLocation]:
        """
        Geocode an address synchronously.
        
        Uses local lookup tables first, falls back to state centroid.
        """
        # Build cache key
        cache_key = f"{address}:{city}:{state}:{zip_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = None
        
        # Try city lookup first
        if city and state:
            city_key = f"{city}, {state}"
            if city_key in US_CITY_COORDINATES:
                lat, lng = US_CITY_COORDINATES[city_key]
                result = GeoLocation(
                    latitude=lat,
                    longitude=lng,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    formatted_address=f"{city}, {state}",
                )
        
        # Fall back to state centroid
        if result is None and state:
            state_upper = state.upper()
            if state_upper in US_STATE_COORDINATES:
                lat, lng = US_STATE_COORDINATES[state_upper]
                result = GeoLocation(
                    latitude=lat,
                    longitude=lng,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    formatted_address=f"{state}",
                )
        
        # Cache result
        if result:
            self._cache[cache_key] = result
        
        return result
    
    async def geocode(
        self,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
    ) -> Optional[GeoLocation]:
        """
        Geocode an address asynchronously.
        
        If API key is provided, uses external service for precise results.
        Otherwise falls back to local lookup.
        """
        # Try local lookup first
        local_result = self.geocode_sync(address, city, state, zip_code)
        
        # If we have an API key and want precise results, use external service
        if self.api_key and address:
            try:
                # Placeholder for external API call
                # In production, integrate with Google Maps, Mapbox, or similar
                pass
            except Exception as e:
                logger.warning(f"External geocoding failed: {e}")
        
        return local_result
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[GeoLocation]:
        """
        Reverse geocode coordinates to an address.
        
        Uses simple distance-based lookup to nearest known city.
        """
        location = GeoLocation(latitude=lat, longitude=lng)
        
        # Find nearest city
        min_distance = float('inf')
        nearest_city = None
        
        for city_name, (city_lat, city_lng) in US_CITY_COORDINATES.items():
            city_location = GeoLocation(latitude=city_lat, longitude=city_lng)
            distance = location.distance_to(city_location)
            
            if distance < min_distance:
                min_distance = distance
                nearest_city = city_name
        
        if nearest_city:
            # Parse city, state from key
            parts = nearest_city.split(", ")
            city = parts[0] if len(parts) > 0 else None
            state = parts[1] if len(parts) > 1 else None
            
            return GeoLocation(
                latitude=lat,
                longitude=lng,
                city=city,
                state=state,
                formatted_address=nearest_city,
            )
        
        return location
    
    def find_shelters_nearby(
        self,
        lat: float,
        lng: float,
        radius_miles: float = 50,
        db_session = None,
    ) -> list:
        """
        Find shelters within a radius of given coordinates.
        
        Note: Requires shelter records to have lat/lng populated.
        """
        if db_session is None:
            return []
        
        from app.models import Shelter
        
        user_location = GeoLocation(latitude=lat, longitude=lng)
        
        # Get all shelters (in production, use PostGIS or similar for efficiency)
        shelters = db_session.query(Shelter).filter(
            Shelter.latitude.isnot(None),
            Shelter.longitude.isnot(None),
        ).all()
        
        nearby = []
        for shelter in shelters:
            shelter_location = GeoLocation(
                latitude=shelter.latitude,
                longitude=shelter.longitude,
            )
            distance = user_location.distance_to(shelter_location)
            
            if distance <= radius_miles:
                nearby.append({
                    "shelter": shelter,
                    "distance_miles": round(distance, 1),
                })
        
        # Sort by distance
        nearby.sort(key=lambda x: x["distance_miles"])
        
        return nearby


# Convenience function
def geocode_shelter(
    city: Optional[str] = None,
    state: Optional[str] = None,
    address: Optional[str] = None,
) -> Optional[Tuple[float, float]]:
    """Quick geocode for a shelter location."""
    geocoder = Geocoder()
    result = geocoder.geocode_sync(address=address, city=city, state=state)
    return result.coordinates if result else None
