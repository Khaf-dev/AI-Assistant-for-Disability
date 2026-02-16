import cv2
import numpy as np
from ultralytics import YOLO  # type: ignore[reportPrivateImportUsage]
import easyocr
from transformers import pipeline
import torch
from typing import List, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class VisionProcessor:
    def __init__(self):
        """Initialize Vision Processor"""
        logger.info("Initializing Vision Processor...")
        
        try:
            # Load models
            self.object_model = YOLO('yolov8n.pt')  # Lightweight YOLOv8 model
            self.text_reader = easyocr.Reader(['en'])
            
            # Scene describer is optional - use fallback for now
            self.scene_describer = None
            logger.info("Scene describer will use manual inference (no pretrained pipeline)")
            
            # Face detector (cv2.data.haarcascades exists at runtime; Pylance stubs may omit it)
            self.face_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore[reportAttributeAccessIssue]
            )
            
            # initialize camera
            self.camera = cv2.VideoCapture(0)
            
            # Load known faces (from database)
            self.known_faces = self._load_known_faces()
            
            logger.info("Vision Processor initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing Vision Processor: {e}")
            raise
    
    def _load_known_faces(self):
        """Load known faces from database"""
        return {}
        
    def capture_image(self, save_path=None):
        """Capture image from camera"""
        try:
            ret, frame = self.camera.read()
            
            if ret and save_path:
                cv2.imwrite(save_path, frame)
            
            return frame if ret else None
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return None
    
    async def describe_scene_detailed(self, image):
        """Generate detailed scene description"""
        try:
            if image is None:
                return "Unable to process image."
            
            # Object detection
            objects = self.object_model(image)
            
            # Text extraction
            texts = await self.extract_text(image)
            
            # Compose description
            description = "Here's what I see: "
            
            if objects:
                # Extract class names from results
                class_names = []
                for result in objects:
                    for box in result.boxes:
                        class_name = result.names[int(box.cls[0])]
                        class_names.append(class_name)
                
                if class_names:
                    obj_list = ', '.join(class_names[:5])
                    description += f"I can see {obj_list}. "
            
            if texts:
                description += f"There's text that says: {' '.join(texts[:2])}"
            
            if not objects and not texts:
                description += "I don't see any notable objects or text."
            
            return description
        
        except Exception as e:
            logger.error(f"Error describing scene: {e}")
            return "I encountered an error processing the image."
    
    async def detect_objects(self, image) -> List[Dict]:
        """Detect objects in image"""
        try:
            # Run YOLO detection
            results = self.object_model(image,verbose=False)
            
            objects = []
            for result in results:
                for box in result.boxes:
                    obj = {
                        'name': result.names[int(box.cls[0])],
                        'confidence': float(box.conf[0]),
                        'bbox': box.xyxy[0].tolist() if hasattr(box, 'xyxy') else []
                    }
                    objects.append(obj)
            
            return objects[:10]  # return top 10 objects
        
        except Exception as e:
            logger.error(f"Error detecting objects: {e}")
            return []
    
    async def extract_text(self, image) -> List[str]:
        """Extract text from image using OCR"""
        try:
            # Convert to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Read text
            results = self.text_reader.readtext(rgb_image)
            
            texts = []
            for (bbox, text, prob) in results:
                confidence = float(prob) if isinstance(prob, (int, float)) else 0.0
                if confidence > 0.5:  # confidence threshold
                    texts.append(text)
            
            return texts
        
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return []
    
    async def recognize_faces(self, image) -> List[Dict]:
        """Recognize faces in image"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5
            )
            
            recognized_faces = []
            for (x, y, w, h) in faces:
                face_info = {
                    'bbox': [x, y, w, h],
                    'name': 'Unknown',
                    'confidence': 0.0
                }
                recognized_faces.append(face_info)
            
            return recognized_faces
        
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return []
    
    async def describe_scene_brief(self, image) -> str:
        """Generate brief scene description"""
        return "Scene captured. Analyzing..."
    
    def cleanup(self):
        """Cleanup resources"""
        if self.camera.isOpened():
            self.camera.release()