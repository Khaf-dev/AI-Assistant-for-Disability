"""Face Recognition Feature - Detects and identifies faces with training capability"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pickle
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

# Try to import face_recognition, fallback to placeholder
try:
    import face_recognition
    HAS_FACE_RECOGNITION = True
except ImportError:
    HAS_FACE_RECOGNITION = False
    logger.warning("face_recognition library not installed. Install with: pip install face_recognition")


class FaceRecognizer:
    """Detects, recognizes, and trains on faces in images"""
    
    def __init__(self, enable_recognition: bool = True, config_path: str = "config.yaml"):
        """
        Initialize face recognizer with optional training capability
        
        Args:
            enable_recognition: Whether to enable face recognition/identification
            config_path: Path to config.yaml for settings
        """
        self.enable_recognition = enable_recognition
        self.config = self._load_config(config_path)
        self.face_config = self.config.get('face_recognition', {})
        
        # Model settings
        self.model = self.face_config.get('model', 'hog')  # hog or cnn
        self.detection_confidence = self.face_config.get('detection_confidence', 0.6)
        self.recognition_confidence = self.face_config.get('recognition_confidence', 0.6)
        self.max_distance = self.face_config.get('max_distance', 0.6)
        self.enable_training = self.face_config.get('enable_training', True)
        self.max_faces_per_person = self.face_config.get('max_faces_per_person', 10)
        
        # Storage
        self.encodings_db = {}  # {person_name: [encodings]}
        self.face_cache = {}  # Cache for detected faces
        self._load_known_faces()
        
        logger.info(f"FaceRecognizer initialized (recognition: {enable_recognition}, model: {self.model})")
    
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
    
    def _load_known_faces(self) -> None:
        """Load known face encodings from disk"""
        try:
            encodings_file = Path('database/face_encodings.pkl')
            if encodings_file.exists():
                with open(encodings_file, 'rb') as f:
                    self.encodings_db = pickle.load(f)
                logger.info(f"Loaded {len(self.encodings_db)} known people")
            else:
                logger.debug("No saved face encodings found. Starting fresh.")
        except Exception as e:
            logger.error(f"Error loading face encodings: {e}")
            self.encodings_db = {}
    
    def _save_known_faces(self) -> None:
        """Save known face encodings to disk"""
        try:
            encodings_file = Path('database/face_encodings.pkl')
            encodings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(encodings_file, 'wb') as f:
                pickle.dump(self.encodings_db, f)
            logger.debug("Face encodings saved successfully")
        except Exception as e:
            logger.error(f"Error saving face encodings: {e}")
    
    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in image frame
        
        Args:
            frame: Input image frame (numpy array)
        
        Returns:
            List of detected faces with coordinates and encodings
        """
        try:
            if frame is None or frame.size == 0:
                return []
            
            if not HAS_FACE_RECOGNITION:
                logger.warning("face_recognition library not available")
                return []
            
            # Convert BGR to RGB if needed (OpenCV uses BGR)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = frame[:, :, ::-1]
            else:
                frame_rgb = frame
            
            # Detect face locations (face_recognition lib has no type stubs)
            face_locations = face_recognition.face_locations(  # type: ignore[reportAttributeAccessIssue]
                frame_rgb,
                model=self.model
            )
            face_encodings = face_recognition.face_encodings(  # type: ignore[reportAttributeAccessIssue]
                frame_rgb,
                face_locations
            )
            
            # Create face objects
            faces = []
            for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                faces.append({
                    'id': len(faces),
                    'top': int(top),
                    'right': int(right),
                    'bottom': int(bottom),
                    'left': int(left),
                    'encoding': encoding,
                    'identity': 'Unknown',
                    'confidence': 0.0
                })
            
            logger.debug(f"Detected {len(faces)} faces")
            return faces
        
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def recognize_faces(self, faces: List[Dict]) -> List[Dict]:
        """
        Recognize/identify detected faces using stored encodings
        
        Args:
            faces: List of detected face objects with encodings
        
        Returns:
            List of faces with identification results
        """
        if not self.enable_recognition or not faces or not HAS_FACE_RECOGNITION:
            return faces
        
        try:
            for face in faces:
                encoding = face.get('encoding')
                if encoding is None:
                    continue
                
                # Compare against known faces
                best_match_name = 'Unknown'
                best_match_distance = float('inf')
                
                for person_name, known_encodings in self.encodings_db.items():
                    for known_encoding in known_encodings:
                        distance = face_recognition.face_distance([known_encoding], encoding)[0]  # type: ignore[reportAttributeAccessIssue]
                        
                        if distance < best_match_distance:
                            best_match_distance = distance
                            best_match_name = person_name
                
                # Set identity if match confidence is high enough
                if best_match_distance <= self.max_distance:
                    face['identity'] = best_match_name
                    face['confidence'] = 1.0 - best_match_distance
                    logger.debug(f"Recognized: {best_match_name} (confidence: {face['confidence']:.2f})")
                else:
                    face['identity'] = 'Unknown'
                    face['confidence'] = 0.0
            
            return faces
        
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return faces
    
    def enroll_face(self, person_name: str, face_encoding: np.ndarray) -> bool:
        """
        Register a new face for future identification (training)
        
        Args:
            person_name: Name of the person
            face_encoding: Face encoding/embedding vector
        
        Returns:
            True if enrollment successful, False otherwise
        """
        if not self.enable_training or not HAS_FACE_RECOGNITION:
            logger.warning("Face training is disabled or library not available")
            return False
        
        try:
            # Initialize list for this person if needed
            if person_name not in self.encodings_db:
                self.encodings_db[person_name] = []
            
            # Check max samples per person
            if len(self.encodings_db[person_name]) >= self.max_faces_per_person:
                logger.warning(f"Maximum samples reached for {person_name}")
                return False
            
            # Add encoding
            self.encodings_db[person_name].append(face_encoding)
            logger.info(f"Enrolled face for {person_name} ({len(self.encodings_db[person_name])} samples)")
            
            # Auto-save if configured
            if self.face_config.get('auto_save_encodings', True):
                self._save_known_faces()
            
            return True
        
        except Exception as e:
            logger.error(f"Error enrolling face: {e}")
            return False
    
    def enroll_from_image(self, person_name: str, frame: np.ndarray) -> bool:
        """
        Detect face in image and enroll it
        
        Args:
            person_name: Name of the person
            frame: Image frame containing the face
        
        Returns:
            True if enrollment successful
        """
        try:
            faces = self.detect_faces(frame)
            if not faces:
                logger.warning(f"No faces detected in image for {person_name}")
                return False
            
            # Use first detected face
            face = faces[0]
            return self.enroll_face(person_name, face['encoding'])
        
        except Exception as e:
            logger.error(f"Error enrolling from image: {e}")
            return False
    
    def remove_person(self, person_name: str) -> bool:
        """
        Remove a person from known faces database
        
        Args:
            person_name: Name of the person to remove
        
        Returns:
            True if removed successfully
        """
        try:
            if person_name in self.encodings_db:
                del self.encodings_db[person_name]
                self._save_known_faces()
                logger.info(f"Removed {person_name} from database")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing person: {e}")
            return False
    
    def get_known_people(self) -> List[str]:
        """Get list of enrolled people"""
        return list(self.encodings_db.keys())
    
    def add_known_face(self, person_name: str, face_encoding: np.ndarray) -> None:
        """(Deprecated) Use enroll_face instead"""
        self.enroll_face(person_name, face_encoding)
    
    def get_face_description(self, faces: List[Dict]) -> str:
        """
        Generate description of detected faces
        
        Args:
            faces: List of detected faces
        
        Returns:
            Formatted face description
        """
        if not faces:
            return "No faces detected."
        
        if len(faces) == 1:
            face = faces[0]
            identity = face.get('identity', 'Unknown')
            confidence = face.get('confidence', 0)
            
            if identity != 'Unknown':
                return f"I detected {identity} (confidence: {confidence:.1%})."
            else:
                return "I detected one unknown face."
        else:
            # Count unknown vs known
            unknown_count = sum(1 for f in faces if f.get('identity') == 'Unknown')
            known_count = len(faces) - unknown_count
            
            description_parts = [f"I detected {len(faces)} faces:"]
            
            if known_count > 0:
                description_parts.append(f"{known_count} recognized")
            if unknown_count > 0:
                description_parts.append(f"{unknown_count} unknown")
            
            return " - ".join(description_parts) + "."
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get face recognition statistics"""
        return {
            'total_known_people': len(self.encodings_db),
            'total_encodings': sum(len(e) for e in self.encodings_db.values()),
            'people': {
                name: len(encodings) 
                for name, encodings in self.encodings_db.items()
            },
            'library_available': HAS_FACE_RECOGNITION,
            'model': self.model
        }

