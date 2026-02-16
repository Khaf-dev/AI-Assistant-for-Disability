from openai import OpenAI
from typing import Dict, List, Any, Optional, cast
import json
import torch
from transformers import AutoModelForCausalLM, pipeline, AutoTokenizer
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class LLMHandler:
    """Language Model Handler for intent recognition and responses"""
    
    def __init__(self, use_openai: bool = True):
        """Initialize LLM Handler"""
        logger.info("Initializing LLM Handler...")
        
        self.use_openai = use_openai
        self.model = None
        self.client = None
        
        if use_openai:
            # Initialize OpenAI client with API key from environment
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.model = "gpt-3.5-turbo"
                logger.info("Using OpenAI for LLM")
            else:
                logger.warning("OpenAI API key not found, falling back to local model")
                self.use_openai = False
        else:
            logger.info("Using local model for LLM")
        
        # Conversation history
        self.conversation_history = []
        
        # Predefined intents (expanded for offline fallback when API unavailable)
        self.intents = {
            'describe_scene': [
                'describe', 'what do you see', 'what around', 'surroundings', 'scene', 'what do you notice',
                'analyze', 'what\'s around', 'whats around', 'tell me about', 'what is there', 'look around'
            ],
            'read_text': [
                'read', 'what does it say', 'text', 'read text', 'read the text', 'any text', 'letters',
                'words', 'sign', 'label', 'ocr'
            ],
            'recognize_objects': [
                'objects', 'what things', 'identify', 'what objects', 'detect objects', 'what do you detect',
                'things around', 'items'
            ],
            'navigate': [
                'go to', 'navigate', 'directions to', 'how to get to', 'take me to', 'route to', 'way to',
                'directions', 'where is', 'guide me to', 'walk to'
            ],
            'recognize_people': [
                'who is this', 'identify person', 'do you know this person', 'who do you see', 'faces',
                'recognize', 'who is here', 'anyone', 'people', 'who\'s there', 'whos there'
            ],
            'emergency': [
                'emergency', 'danger', 'call for help', 'sos', 'i need help', 'need help now', 'alert',
                'fall', 'fallen', 'hurt', '911', 'urgent', 'im hurt', 'i\'m hurt', 'help me i\'m', 'help i\'m'
            ],
            'exit': [
                'goodbye', 'bye', 'exit', 'quit', 'stop', 'turn off', 'shut down', 'close', 'leave',
                'that\'s all', 'thats all', 'done', 'finish', 'end'
            ],
            'general_question': ['what', 'how', 'why', 'when', 'where']
        }
        
    
    async def understand_intent(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Understand user intent from command"""
        if context is None:
            context = {}
        
        try:
            if self.use_openai and self.client and self.model:
                # Use GPT for intent recognition
                prompt = f"""
                User command: {command}
                
                Classify the intent and extract parameters.
                Intent options: describe_scene, read_text, recognize_objects, navigate, recognize_people, emergency, exit, general_question
                
                Return JSON format: {{"action": "action_name", "parameters": {{}}}}
                """
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=cast(Any, [{"role": "user", "content": prompt}]),
                    temperature=0.1,
                    max_tokens=100
                )
                content = response.choices[0].message.content
                if not content:
                    return self._keyword_intent(command)
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.lower().startswith("json"):
                        content = content[4:]
                result = json.loads(content.strip())
                if isinstance(result, dict) and "action" in result:
                    return result
                return self._keyword_intent(command)
            
            else:
                # Use keyword matching for local intent recognition
                return self._keyword_intent(command)
        
        except Exception as e:
            logger.error(f"Error understanding intent: {e}")
            return self._keyword_intent(command)
    
    def _keyword_intent(self, command: str) -> Dict:
        """Local keyword-based intent (used when offline or API fails). Longest match wins."""
        cmd_lower = command.lower().strip()
        best_intent = None
        best_keyword_len = 0
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                kw_lower = keyword.lower()
                if kw_lower in cmd_lower and len(kw_lower) > best_keyword_len:
                    best_keyword_len = len(kw_lower)
                    best_intent = intent
        if best_intent is None:
            return {"action": "general_question", "parameters": {"query": command}}
        params = {"query": command}
        if best_intent == "navigate":
            parts = command.split()
            for i, w in enumerate(parts):
                if w.lower() in ("to", "toward", "towards") and i + 1 < len(parts):
                    params["destination"] = " ".join(parts[i + 1:])
                    break
        return {"action": best_intent, "parameters": params}
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate natural language response"""
        if context is None:
            context = {}
        
        try:
            if self.use_openai and self.client and self.model:
                messages: List[Dict[str, str]] = [
                    {"role": "system", "content": "You are a helpful assistant for visually impaired people."},
                    {"role": "user", "content": query}
                ]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=cast(Any, messages),
                    temperature=0.7,
                    max_tokens=200
                )
                content = response.choices[0].message.content
                return content if content is not None else ""
            
            else:
                # Local model response
                return f"Understood: {query}."
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error processing your request."
    
    async def generate_scene_description(
        self,
        objects: Optional[List[Any]] = None,
        texts: Optional[List[Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate scene natural description"""
        if objects is None:
            objects = []
        if texts is None:
            texts = []
        if context is None:
            context = {}
        
        description = "Here's what I can describe: "
        
        if objects:
            description += f"I see {', '.join(objects)}. "
        
        if texts:
            description += f"I found text: {', '.join(texts)}. "
        
        if not objects and not texts:
            description += "I don't detect any notable objects or text in the current scene."
        
        return description