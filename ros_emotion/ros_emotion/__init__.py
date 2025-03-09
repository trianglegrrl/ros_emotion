# Import emotion_model for easier access
from . import emotion_model 
from . import personality_model

# Import factory function for easier creation of models
from .emotion_model import create_emotion_model
from .personality_model import create_personality_model 