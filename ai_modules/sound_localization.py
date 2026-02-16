"""Sound Localization Module - Detects and localizes audio sources for navigation assistance"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import yaml
import threading
import queue
from collections import deque
import time

logger = logging.getLogger(__name__)

# Try to import audio libraries
try:
    import pyaudio
    import struct
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    logger.warning("pyaudio not installed. Install with: pip install pyaudio")

try:
    import librosa
    import scipy.signal
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    logger.warning("librosa not installed. Install with: pip install librosa scipy")


class SoundLocalizer:
    """Detects and localizes sound sources in real-time"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize sound localization system
        
        Args:
            config_path: Path to config.yaml
        """
        self.config = self._load_config(config_path)
        self.sound_config = self.config.get('sound_localization', {})
        device_profile = self.config.get('device', {}).get('profile', 'desktop')
        
        # Audio settings (optionally reduced for edge/low-memory profiles)
        self.enabled = self.sound_config.get('enabled', True)
        base_rate = self.sound_config.get('sample_rate', 16000)
        base_chunk = self.sound_config.get('chunk_size', 1024)
        if device_profile == 'raspberry_pi':
            self.sample_rate = min(base_rate, 8000)
            self.chunk_size = max(512, base_chunk // 2)
        elif device_profile == 'low_memory':
            self.sample_rate = min(base_rate, 8000)
            self.chunk_size = max(256, base_chunk // 2)
        else:
            self.sample_rate = base_rate
            self.chunk_size = base_chunk
        self.channels = self.sound_config.get('channels', 1)
        self._device_profile = device_profile
        
        # Detection settings
        detection_config = self.sound_config.get('detection', {})
        self.min_frequency = detection_config.get('min_frequency', 50)
        self.max_frequency = detection_config.get('max_frequency', 8000)
        self.noise_threshold = detection_config.get('noise_threshold', -40)
        self.sound_sensitivity = detection_config.get('sound_sensitivity', 0.5)
        
        # Localization settings
        localization_config = self.sound_config.get('localization', {})
        self.localization_method = localization_config.get('method', 'beamforming')
        self.num_directions = localization_config.get('num_directions', 8)
        self.angle_resolution = localization_config.get('angle_resolution', 45)
        self.max_range = localization_config.get('max_range', 10)
        
        # Obstacle settings
        obstacle_config = self.sound_config.get('obstacles', {})
        self.obstacle_detection = obstacle_config.get('enabled', True)
        self.warning_threshold = obstacle_config.get('warning_threshold', 2.0)
        
        # Audio buffer for processing
        self.audio_buffer = deque(maxlen=self.chunk_size * 4)
        self.detected_sounds = []
        self.localized_sounds = []
        
        # Recording state
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.p: Optional[Any] = pyaudio.PyAudio() if HAS_PYAUDIO else None
        self.stream: Optional[Any] = None
        
        logger.info(
            f"SoundLocalizer initialized (enabled: {self.enabled}, method: {self.localization_method}, "
            f"profile: {self._device_profile})"
        )
    
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
    
    def start_listening(self) -> bool:
        """Start listening for audio input"""
        if not HAS_PYAUDIO or self.p is None:
            logger.warning("PyAudio not available for recording")
            return False
        
        try:
            if self.stream is None:
                self.stream = self.p.open(
                    format=pyaudio.paFloat32,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    start=False
                )
            
            self.is_recording = True
            if self.stream is not None:
                self.stream.start_stream()
            logger.info("Sound localization listening started")
            return True
        
        except Exception as e:
            logger.error(f"Error starting audio stream: {e}")
            return False
    
    def stop_listening(self) -> None:
        """Stop listening for audio"""
        try:
            self.is_recording = False
            if self.stream:
                self.stream.stop_stream()
            logger.info("Sound localization listening stopped")
        except Exception as e:
            logger.error(f"Error stopping audio stream: {e}")
    
    def get_audio_chunk(self) -> Optional[np.ndarray]:
        """Get audio chunk from microphone"""
        if not HAS_PYAUDIO or not self.stream:
            return None
        
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            audio_chunk = np.frombuffer(data, dtype=np.float32)
            return audio_chunk
        except Exception as e:
            logger.error(f"Error reading audio: {e}")
            return None
    
    def detect_sounds(self, audio_chunk: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect sound events in audio chunk
        
        Args:
            audio_chunk: Audio samples to analyze
        
        Returns:
            List of detected sounds with properties
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return []
        
        try:
            detected = []
            
            # Calculate power
            power_db = 20 * np.log10(np.sqrt(np.mean(audio_chunk ** 2)) + 1e-10)
            
            # Check if sound exceeds noise threshold
            if power_db > self.noise_threshold:
                detected.append({
                    'type': 'sound_event',
                    'power_db': float(power_db),
                    'confidence': float(np.clip((power_db - self.noise_threshold) / 20.0, 0, 1)),
                    'timestamp': time.time()
                })
            
            # Try frequency analysis
            if HAS_LIBROSA:
                # Compute STFT
                stft = librosa.stft(audio_chunk)
                magnitude = np.abs(stft)
                
                # Find dominant frequency
                if magnitude.size > 0:
                    freq_idx = np.argmax(np.mean(magnitude, axis=1))
                    freq_hz = librosa.fft_frequencies(sr=self.sample_rate)[freq_idx]
                    
                    if self.min_frequency <= freq_hz <= self.max_frequency:
                        detected.append({
                            'type': 'frequency_tone',
                            'frequency_hz': float(freq_hz),
                            'power_db': float(power_db),
                            'timestamp': time.time()
                        })
            
            return detected
        
        except Exception as e:
            logger.debug(f"Error detecting sounds: {e}")
            return []
    
    def localize_sound(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Localize sound source direction
        
        Args:
            audio_chunk: Audio to analyze
        
        Returns:
            Dictionary with localization info (angle, distance, confidence)
        """
        if audio_chunk is None or len(audio_chunk) < self.chunk_size:
            return None
        
        try:
            # Simple energy-based direction estimation for mono audio
            # In production, use stereo/multi-microphone array for true localization
            
            # Calculate envelope
            try:
                if HAS_LIBROSA:
                    audio_float = np.asarray(audio_chunk, dtype=np.float64)
                    analytic_signal = scipy.signal.hilbert(audio_float)  # type: ignore
                    # Calculate magnitude from complex signal safely
                    envelope = np.abs(analytic_signal)  # type: ignore
                else:
                    envelope = np.asarray(audio_chunk, dtype=np.float64)
            except (TypeError, AttributeError, ValueError):
                # Fallback: use simple absolute value
                envelope = np.asarray(np.abs(audio_chunk), dtype=np.float64)
            
            # Estimate direction based on signal peaks
            # Simplified: returns potential sound direction
            peak_idx = np.argmax(envelope)
            direction_ratio = peak_idx / len(envelope)
            
            # Map to angles (for 8-bin localization: 0-360 degrees)
            estimated_angle = (direction_ratio * 360) % 360
            
            # Estimate distance (simplified - based on signal strength)
            signal_strength = np.max(envelope)
            estimated_distance = max(0.5, min(self.max_range, self.max_range / (signal_strength + 0.1)))
            
            return {
                'angle_degrees': float(estimated_angle),
                'distance_meters': float(estimated_distance),
                'confidence': float(np.clip(signal_strength, 0, 1)),
                'direction': self._angle_to_direction(estimated_angle),
                'timestamp': time.time()
            }
        
        except Exception as e:
            logger.debug(f"Error localizing sound: {e}")
            return None
    
    def _angle_to_direction(self, angle_degrees: float) -> str:
        """Convert angle to compass direction"""
        directions = ['Front', 'Front-Right', 'Right', 'Back-Right', 
                     'Back', 'Back-Left', 'Left', 'Front-Left']
        
        bin_size = 360 / len(directions)
        bin_idx = int((angle_degrees + bin_size / 2) / bin_size) % len(directions)
        return directions[bin_idx]
    
    def detect_obstacles(self, audio_chunk: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect potential obstacles based on audio reflections/echoes
        
        Args:
            audio_chunk: Audio to analyze for echoes
        
        Returns:
            List of potential obstacles
        """
        if not self.obstacle_detection or audio_chunk is None:
            return []
        
        try:
            obstacles = []
            
            # Detect echoes/reflections
            # Calculate autocorrelation to find delayed reflections
            normalized = audio_chunk / (np.max(np.abs(audio_chunk)) + 1e-10)
            
            # Look for repeated patterns (echoes)
            max_lag = min(self.sample_rate // 100, len(normalized) // 2)  # 10ms max
            
            for lag in range(self.chunk_size // 8, max_lag, self.chunk_size // 16):
                if lag < len(normalized):
                    correlation = np.corrcoef(normalized[:-lag], normalized[lag:])[0, 1]
                    
                    if correlation > 0.5:  # Strong echo detected
                        # Estimate distance from echo delay
                        delay_seconds = lag / self.sample_rate
                        # Speed of sound ~343 m/s, divide by 2 for round trip
                        distance = min(self.max_range, (delay_seconds * 343) / 2.0)
                        
                        if distance < self.warning_threshold:
                            obstacles.append({
                                'type': 'echo',
                                'estimated_distance_meters': float(distance),
                                'confidence': float(correlation),
                                'warning': True,
                                'timestamp': time.time()
                            })
            
            return obstacles
        
        except Exception as e:
            logger.debug(f"Error detecting obstacles: {e}")
            return []
    
    def classify_sound(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Classify type of sound (speech, alarm, door, etc.)
        
        Args:
            audio_chunk: Audio to classify
        
        Returns:
            Sound classification with confidence
        """
        if not self.sound_config.get('audio_classification', {}).get('enabled', False):
            return None
        
        try:
            # Simplified sound classification
            power_db = 20 * np.log10(np.sqrt(np.mean(audio_chunk ** 2)) + 1e-10)
            
            # Get frequency characteristics
            classifications = {}
            
            if HAS_LIBROSA:
                # Compute spectral features
                stft = librosa.stft(audio_chunk)
                magnitude = np.abs(stft)
                
                spectral_centroid = librosa.feature.spectral_centroid(S=magnitude, sr=self.sample_rate)[0][0]
                zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_chunk)[0][0]
                
                # Simple heuristics
                if spectral_centroid < 1000:  # Low frequency
                    classifications['speech'] = 0.6
                    classifications['door'] = 0.3
                    classifications['alarm'] = 0.1
                elif spectral_centroid > 4000:  # High frequency
                    classifications['alarm'] = 0.7
                    classifications['door'] = 0.2
                    classifications['speech'] = 0.1
                else:
                    classifications['speech'] = 0.5
                    classifications['ambient'] = 0.3
                    classifications['other'] = 0.2
            else:
                classifications['unknown'] = 1.0
            
            # Find top classification
            top_class = max(classifications.items(), key=lambda x: x[1])
            
            return {
                'primary_sound': top_class[0],
                'confidence': float(top_class[1]),
                'all_classifications': classifications,
                'power_db': float(power_db),
                'timestamp': time.time()
            }
        
        except Exception as e:
            logger.debug(f"Error classifying sound: {e}")
            return None
    
    def get_audio_description(self, sounds: List[Dict]) -> str:
        """
        Generate natural language description of detected sounds
        
        Args:
            sounds: List of detected/localized sounds
        
        Returns:
            Natural language description
        """
        if not sounds:
            return "No sounds detected."
        
        descriptions = []
        
        for sound in sounds:
            if sound['type'] == 'sound_event':
                power = sound['power_db']
                if power > 0:
                    descriptions.append(f"Loud sound detected ({power:.0f} dB)")
                else:
                    descriptions.append("Quiet sound detected")
            
            elif sound['type'] == 'frequency_tone':
                freq = sound['frequency_hz']
                descriptions.append(f"Tone at {freq:.0f} Hertz")
        
        return " ".join(descriptions) if descriptions else "Audio detected"
    
    def get_localization_summary(self, localization: Dict) -> str:
        """Generate description of sound localization"""
        if not localization:
            return "Unable to localize sound"
        
        direction = localization.get('direction', 'Unknown')
        distance = localization.get('distance_meters', 0)
        confidence = localization.get('confidence', 0)
        
        return f"Sound detected {direction} at approximately {distance:.1f} meters (confidence: {confidence:.0%})"
    
    def cleanup(self) -> None:
        """Clean up audio resources"""
        try:
            self.stop_listening()
            if self.stream:
                self.stream.close()
            if self.p:
                self.p.terminate()
            logger.info("Sound localization cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get sound localization statistics"""
        return {
            'enabled': self.enabled,
            'method': self.localization_method,
            'sample_rate': self.sample_rate,
            'obstacle_detection': self.obstacle_detection,
            'audio_classification': self.sound_config.get('audio_classification', {}).get('enabled', False),
            'library_available': HAS_PYAUDIO and HAS_LIBROSA,
            'buffer_size': len(self.audio_buffer)
        }
