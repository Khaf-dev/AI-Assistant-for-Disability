import requests
from typing import Dict, List, Tuple, Optional, Any, cast
import json
from geopy.geocoders import Nominatim
import geocoder
from math import radians, sin, cos, sqrt, atan2
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

class NavigationAssistant:
    current_route: Optional[Dict[str, Any]]
    current_location: Optional[Dict[str, Any]]
    next_waypoint_idx: int

    def __init__(self, config_path: str = "config.yaml"):
        print("Initializing Navigation Assistant...")
        self.config = self._load_config(config_path)
        self.nav_config = self.config.get('navigation', {})
        self.sound_config = self.config.get('sound_localization', {})
        
        self.geolocator = Nominatim(user_agent="vision_assistant")
        self.api_keys = self._load_api_keys()
        
        # Audio guidance settings
        self.audio_guidance_enabled = self.nav_config.get('audio_guidance', True)
        self.voice_directions_frequency = self.nav_config.get('voice_directions_frequency', 'periodic')
        
        # Navigation state
        self.current_route = None
        self.next_waypoint_idx = 0
        self.current_location = None
        
        logger.info(f"NavigationAssistant initialized (audio_guidance: {self.audio_guidance_enabled})")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            return {}
        
    async def get_current_location(self) -> Optional[Dict]:
        """Get current location using IP or GPS. Returns None on failure."""
        try:
            # Try to get location from IP
            g = geocoder.ip('me')
            if g.ok:
                return {
                    'latitude': g.latlng[0],
                    'longitude': g.latlng[1],
                    'address': g.address,
                    'city': g.city,
                    'country': g.country
                }
            # Fallback when IP geolocation fails (e.g. no network or not available)
            logger.warning("IP geolocation failed or unavailable")
            return None
        except Exception as e:
            logger.warning(f"Location error: {e}")
            return None
        
        
    async def get_directions(self, start: Optional[Dict], destination: str) -> Dict:
        """Get directions to destination. start may be None if location unknown."""
        if not start or not isinstance(start, dict):
            return {"error": "Current location could not be determined. Please check network or specify a starting address."}
        if start.get('latitude') is None or start.get('longitude') is None:
            return {"error": "Current location has no valid coordinates."}

        # Geocode destination (sync call; cast for type checker if stubs are wrong)
        dest_location = cast(Any, self.geolocator.geocode(destination))
        if not dest_location:
            return {"error": "Destination not found"}
        dest_lat = getattr(dest_location, "latitude", None)
        dest_lon = getattr(dest_location, "longitude", None)
        if dest_lat is None or dest_lon is None:
            return {"error": "Destination coordinates could not be determined."}

        # Use OpenStreetMap or Google Maps API
        directions = await self._get_osm_route(
            (start['latitude'], start['longitude']),
            (dest_lat, dest_lon)
        )
        
        return {
            'destination': destination,
            'distance': directions.get('distance', 'Unknown'),
            'duration': directions.get('duration', 'Unknown'),
            'steps': self._simplify_instructions(directions.get('steps', []))
        }
        
    async def _get_osm_route(self, start: Tuple, end: Tuple) -> Dict:
        """Get route from OpenStreetMap"""
        try:
            url = "http://router.project-osrm.org/route/v1/walking/{},{};{},{}"
            url = url.format(start[1], start[0], end[1], end[0])
            
            response = requests.get(url, params={
                "overview": "false",
                "alternatives": "false",
                "steps": "true"
            })
            
            data = response.json()
            
            if data.get('routes'):
                route = data['routes'][0]
                return {
                    'distance': route['distance'],
                    'duration': route['duration'],
                    'steps': route['legs'][0]['steps']
                }
                
        except Exception as e:
            print(f"Routing error: {e}")
            
        return {}
    
    def _simplify_instructions(self, steps: List) -> List[Dict]:
        """Simplify navigation instructions for speech"""
        simplified = []
        
        for i, step in enumerate(steps[:5]): # Limit to first 5 steps
            instruction = step.get('maneuver', {}).get('instruction', '')
            
            if not instruction:
                # Create simple instruction
                distance = step.get('distance', 0)
                if distance > 0:
                    if distance < 10:
                        instruction = f"Take a few steps"
                    elif distance < 50:
                        instruction = f"Walk about {int(distance)} meters"
                    else:
                        instruction = f"Continue for about {int(distance)} meters"
                        
            simplified.append({
                'instruction': instruction,
                'distance': step.get('distance', 0)
            })
            
        return simplified
    
    async def get_nearby_places(self, category: str, radius: int = 500) -> List[Dict]:
        """Find nearby places of interest"""
        if self.current_location is None:
            return []
        lat = self.current_location.get('latitude')
        lon = self.current_location.get('longitude')
        if lat is None or lon is None:
            return []

        # Use Overpass API for OpenStreetMap
        query = f"""
        [out:json];
        (
            node["amenity"="{category}"](around:{radius},{lat},{lon});
            node["shop"="{category}"](around:{radius},{lat},{lon});
        );
        
        out body;
        """
        
        try:
            response = requests.post(
                "https://overpass-api.de/api/interpreter",
                data={'data': query}
            )
            
            places = []
            for element in response.json().get('elements', []):
                places.append({
                    'name': element.get('tags', {}).get('name', 'Unnamed'),
                    'type': category,
                    'distance': self._calculate_distance(
                        (lat, lon),
                        (element['lat'], element['lon'])
                    )
                })
                
            return sorted(places, key=lambda x: x['distance'])[:5]
        
        except Exception as e:
            print(f"Nearby places error: {e}")
            return []
        
    def _calculate_distance(self, coord1: Tuple, coord2: Tuple) -> float:
        """Calculate distance between two coordinates in meters"""
        # Haversine formula
        R = 6371000 # Earth radius in meters
        
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])
        
        dlat1 = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat1 / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    async def _send_emergency_alert(self, contacts: List[str]):
        """Send emergency alert to contacts"""
        print(f"Sending emergency alert to: {contacts}")
        
        # This would integrate with SMS/Email APIs
        # For demonstration, just print
        for contact in contacts:
            print(f"Alert sent to {contact}")
    
    async def get_audio_guidance(self, sound_info: Dict) -> Optional[str]:
        """
        Get navigation guidance based on detected sounds
        
        Args:
            sound_info: Sound localization info with angle and distance
        
        Returns:
            Navigation guidance as string
        """
        if not self.audio_guidance_enabled or not sound_info:
            return None
        
        try:
            direction = sound_info.get('direction', 'Front')
            distance = sound_info.get('distance_meters', 0)
            confidence = sound_info.get('confidence', 0)
            
            if confidence < 0.5:
                return "Sound detected but low confidence. Please listen carefully."
            
            # Provide navigation guidance
            if distance < 1.0:
                guidance = f"Sound is very close, {distance:.1f} meters {direction}"
            elif distance < 5.0:
                guidance = f"Sound detected {distance:.1f} meters {direction}"
            else:
                guidance = f"Distant sound detected {direction}"
            
            return guidance
        
        except Exception as e:
            logger.error(f"Error getting audio guidance: {e}")
            return None
    
    async def assist_with_obstacles(self, obstacles: List[Dict]) -> Optional[str]:
        """
        Provide navigation assistance based on detected obstacles
        
        Args:
            obstacles: List of detected obstacles from sound
        
        Returns:
            Warning/guidance about obstacles
        """
        if not obstacles:
            return "No obstacles detected. Path is clear."
        
        try:
            warnings = []
            
            for obstacle in obstacles:
                distance = obstacle.get('estimated_distance_meters', 0)
                obs_type = obstacle.get('type', 'unknown')
                confidence = obstacle.get('confidence', 0)
                
                if distance < 1.0:
                    warnings.append(f"CAREFUL: {obs_type} detected {distance:.1f} meters ahead!")
                elif distance < 3.0:
                    warnings.append(f"Warning: {obs_type} at {distance:.1f} meters")
            
            return " ".join(warnings) if warnings else "Possible obstacles in your path. Proceed with caution."
        
        except Exception as e:
            logger.error(f"Error assisting with obstacles: {e}")
            return None
    
    async def get_next_direction(self, current_sound: Optional[Dict] = None) -> Optional[str]:
        """
        Get next navigation direction, optionally using sound cues
        
        Args:
            current_sound: Optional sound localization info for guidance
        
        Returns:
            Next direction instruction
        """
        if not self.current_route or self.next_waypoint_idx >= len(self.current_route.get('steps', [])):
            return "Route complete."
        
        try:
            current_step = self.current_route['steps'][self.next_waypoint_idx]
            instruction = current_step.get('instruction', 'Continue forward')
            
            # Enhance with audio guidance if available
            if current_sound and self.audio_guidance_enabled:
                direction = current_sound.get('direction', '')
                if direction:
                    instruction += f" (Sound detected {direction})"
            
            return instruction
        
        except Exception as e:
            logger.error(f"Error getting next direction: {e}")
            return None
    
    def advance_waypoint(self) -> bool:
        """
        Advance to the next route step (e.g. after user says "I've moved" or "Next step").
        Returns True if advanced, False if no route or already at end.
        """
        if not self.current_route:
            return False
        steps = self.current_route.get('steps') or []
        if self.next_waypoint_idx >= len(steps):
            return False
        self.next_waypoint_idx += 1
        logger.info(f"Waypoint advanced to index {self.next_waypoint_idx}/{len(steps)}")
        return True

    def set_audio_guidance(self, enabled: bool) -> None:
        """Enable/disable audio-assisted navigation"""
        self.audio_guidance_enabled = enabled
        logger.info(f"Audio guidance {'enabled' if enabled else 'disabled'}")
            
    def _load_api_keys(self):
        """Load API keys from configuration"""
        # Load from environment or config file
        return {
            'google_maps': None,
            'openweather': None,
            'twilio': None # For SMS alerts
        }