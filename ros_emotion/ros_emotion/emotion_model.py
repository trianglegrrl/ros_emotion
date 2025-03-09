#!/usr/bin/env python3

import numpy as np
from abc import ABC, abstractmethod
try:
    # For running as a ROS node
    from ros_emotion.msg import EmotionalState
    import ros_emotion.utils as utils
except ImportError:
    # For testing within the package
    from ..msg import EmotionalState
    from . import utils

class EmotionModel(ABC):
    """
    Abstract base class for emotion models.
    This provides a common interface for different emotion models that can be used in the system.
    """
    
    @abstractmethod
    def create_emotional_state(self):
        """Create a new emotional state message"""
        pass
    
    @abstractmethod
    def get_primary_emotion(self, emotional_state):
        """Determine the primary emotion based on the current state"""
        pass
    
    @abstractmethod
    def update_state(self, emotional_state, time_diff, decay_rates):
        """Update the emotional state based on decay rates"""
        pass
    
    @abstractmethod
    def modify_state(self, emotional_state, modification_type, value, specific_emotion=None):
        """Modify the emotional state based on the modification type"""
        pass
    
    @abstractmethod
    def get_all_emotions(self):
        """Return a list of all supported emotion names"""
        pass
    
    @abstractmethod
    def get_emotion_value(self, emotional_state, emotion_name):
        """Get the value of a specific emotion"""
        pass
    
    @abstractmethod
    def set_emotion_value(self, emotional_state, emotion_name, value):
        """Set the value of a specific emotion"""
        pass
    
    @abstractmethod
    def calculate_intensity(self, emotional_state):
        """Calculate the overall intensity of the emotional state"""
        pass
    
    @abstractmethod
    def get_emotion_color(self, emotion_name):
        """Get a color representing a specific emotion"""
        pass
    
    @abstractmethod
    def get_dimensions(self):
        """Return a list of emotional dimensions (e.g., PAD)"""
        pass


class PADBasicEmotionModel(EmotionModel):
    """
    Implementation of the EmotionModel for the PAD + basic emotions model.
    This encapsulates the current emotion model used in the system.
    """
    
    def __init__(self, config=None):
        """Initialize the PAD + basic emotions model"""
        self.config = config or {}
        self.threshold = self.config.get('threshold', 0.05)
        
        # Define the basic emotions supported by this model
        self._basic_emotions = ["happiness", "sadness", "anger", "fear", "disgust", "surprise"]
        
        # Define the dimensions in the PAD model
        self._dimensions = ["pleasure", "arousal", "dominance"]
    
    def create_emotional_state(self):
        """Create a new emotional state message with default values"""
        emotional_state = EmotionalState()
        
        # Set timestamp
        emotional_state.timestamp = utils.get_current_time()
        
        # Initialize PAD dimensions
        emotional_state.pleasure = 0.0
        emotional_state.arousal = 0.0
        emotional_state.dominance = 0.0
        
        # Initialize basic emotions
        emotional_state.happiness = 0.0
        emotional_state.sadness = 0.0
        emotional_state.anger = 0.0
        emotional_state.fear = 0.0
        emotional_state.disgust = 0.0
        emotional_state.surprise = 0.0
        
        # Initialize other fields
        emotional_state.intensity = 0.0
        emotional_state.confidence = 1.0
        emotional_state.source = "initialization"
        emotional_state.description = "Initial emotional state"
        emotional_state.primary_emotion = "neutral"
        
        return emotional_state
    
    def get_primary_emotion(self, emotional_state):
        """Determine the primary emotion based on the current state"""
        emotions = {
            "happiness": emotional_state.happiness,
            "sadness": emotional_state.sadness,
            "anger": emotional_state.anger,
            "fear": emotional_state.fear,
            "disgust": emotional_state.disgust,
            "surprise": emotional_state.surprise
        }
        
        # Find the emotion with the highest value
        primary_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        
        # If all emotions are below threshold, set to neutral
        if emotions[primary_emotion] < self.threshold:
            primary_emotion = "neutral"
        
        return primary_emotion
    
    def update_state(self, emotional_state, time_diff, decay_rates):
        """Update the emotional state based on decay rates"""
        # Update PAD dimensions
        emotional_state.pleasure = utils.emotion_decay(
            emotional_state.pleasure, 
            decay_rates.get('pleasure', 0.01), 
            time_diff
        )
        
        emotional_state.arousal = utils.emotion_decay(
            emotional_state.arousal, 
            decay_rates.get('arousal', 0.02), 
            time_diff
        )
        
        emotional_state.dominance = utils.emotion_decay(
            emotional_state.dominance, 
            decay_rates.get('dominance', 0.005), 
            time_diff
        )
        
        # Update basic emotions
        emotional_state.happiness = utils.emotion_decay(
            emotional_state.happiness, 
            decay_rates.get('happiness', 0.02), 
            time_diff
        )
        
        emotional_state.sadness = utils.emotion_decay(
            emotional_state.sadness, 
            decay_rates.get('sadness', 0.01), 
            time_diff
        )
        
        emotional_state.anger = utils.emotion_decay(
            emotional_state.anger, 
            decay_rates.get('anger', 0.03), 
            time_diff
        )
        
        emotional_state.fear = utils.emotion_decay(
            emotional_state.fear, 
            decay_rates.get('fear', 0.02), 
            time_diff
        )
        
        emotional_state.disgust = utils.emotion_decay(
            emotional_state.disgust, 
            decay_rates.get('disgust', 0.01), 
            time_diff
        )
        
        emotional_state.surprise = utils.emotion_decay(
            emotional_state.surprise, 
            decay_rates.get('surprise', 0.05), 
            time_diff
        )
        
        # Update intensity
        emotional_state.intensity = self.calculate_intensity(emotional_state)
        
        # Update timestamp
        emotional_state.timestamp = utils.get_current_time()
        
        # Update primary emotion
        emotional_state.primary_emotion = self.get_primary_emotion(emotional_state)
        
        return emotional_state
    
    def modify_state(self, emotional_state, modification_type, value, specific_emotion=None):
        """Modify the emotional state based on the modification type"""
        if modification_type == "reset":
            # Create a new emotional state with default values
            new_state = self.create_emotional_state()
            
            # Copy non-emotion fields
            new_state.source = emotional_state.source
            new_state.description = emotional_state.description
            
            return new_state
            
        elif modification_type == "absolute":
            # Set all emotions to the specified value
            emotional_state.pleasure = utils.clamp(value)
            emotional_state.arousal = utils.clamp(value)
            emotional_state.dominance = utils.clamp(value)
            emotional_state.happiness = utils.clamp(value, 0.0, 1.0)
            emotional_state.sadness = utils.clamp(value, 0.0, 1.0)
            emotional_state.anger = utils.clamp(value, 0.0, 1.0)
            emotional_state.fear = utils.clamp(value, 0.0, 1.0)
            emotional_state.disgust = utils.clamp(value, 0.0, 1.0)
            emotional_state.surprise = utils.clamp(value, 0.0, 1.0)
            
        elif modification_type == "relative":
            # Adjust all emotions by the specified value
            emotional_state.pleasure = utils.clamp(emotional_state.pleasure + value)
            emotional_state.arousal = utils.clamp(emotional_state.arousal + value)
            emotional_state.dominance = utils.clamp(emotional_state.dominance + value)
            emotional_state.happiness = utils.clamp(emotional_state.happiness + value, 0.0, 1.0)
            emotional_state.sadness = utils.clamp(emotional_state.sadness + value, 0.0, 1.0)
            emotional_state.anger = utils.clamp(emotional_state.anger + value, 0.0, 1.0)
            emotional_state.fear = utils.clamp(emotional_state.fear + value, 0.0, 1.0)
            emotional_state.disgust = utils.clamp(emotional_state.disgust + value, 0.0, 1.0)
            emotional_state.surprise = utils.clamp(emotional_state.surprise + value, 0.0, 1.0)
            
        elif modification_type == "specific" and specific_emotion:
            # Modify only the specific emotion
            self.set_emotion_value(emotional_state, specific_emotion, value)
        
        # Update intensity
        emotional_state.intensity = self.calculate_intensity(emotional_state)
        
        # Update primary emotion
        emotional_state.primary_emotion = self.get_primary_emotion(emotional_state)
        
        return emotional_state
    
    def get_all_emotions(self):
        """Return a list of all supported emotion names"""
        return self._basic_emotions
    
    def get_emotion_value(self, emotional_state, emotion_name):
        """Get the value of a specific emotion"""
        if emotion_name == "pleasure":
            return emotional_state.pleasure
        elif emotion_name == "arousal":
            return emotional_state.arousal
        elif emotion_name == "dominance":
            return emotional_state.dominance
        elif emotion_name == "happiness":
            return emotional_state.happiness
        elif emotion_name == "sadness":
            return emotional_state.sadness
        elif emotion_name == "anger":
            return emotional_state.anger
        elif emotion_name == "fear":
            return emotional_state.fear
        elif emotion_name == "disgust":
            return emotional_state.disgust
        elif emotion_name == "surprise":
            return emotional_state.surprise
        else:
            raise ValueError(f"Unknown emotion: {emotion_name}")
    
    def set_emotion_value(self, emotional_state, emotion_name, value):
        """Set the value of a specific emotion"""
        if emotion_name == "pleasure":
            emotional_state.pleasure = utils.clamp(value)
        elif emotion_name == "arousal":
            emotional_state.arousal = utils.clamp(value)
        elif emotion_name == "dominance":
            emotional_state.dominance = utils.clamp(value)
        elif emotion_name == "happiness":
            emotional_state.happiness = utils.clamp(value, 0.0, 1.0)
        elif emotion_name == "sadness":
            emotional_state.sadness = utils.clamp(value, 0.0, 1.0)
        elif emotion_name == "anger":
            emotional_state.anger = utils.clamp(value, 0.0, 1.0)
        elif emotion_name == "fear":
            emotional_state.fear = utils.clamp(value, 0.0, 1.0)
        elif emotion_name == "disgust":
            emotional_state.disgust = utils.clamp(value, 0.0, 1.0)
        elif emotion_name == "surprise":
            emotional_state.surprise = utils.clamp(value, 0.0, 1.0)
        else:
            raise ValueError(f"Unknown emotion: {emotion_name}")
        
        return emotional_state
    
    def calculate_intensity(self, emotional_state):
        """Calculate the overall intensity of the emotional state"""
        # Method 1: Average of PAD dimensions (absolute values)
        pad_intensity = (abs(emotional_state.pleasure) + 
                        abs(emotional_state.arousal) + 
                        abs(emotional_state.dominance)) / 3.0
        
        # Method 2: Average of basic emotions
        basic_emotions = [
            emotional_state.happiness,
            emotional_state.sadness,
            emotional_state.anger,
            emotional_state.fear,
            emotional_state.disgust,
            emotional_state.surprise
        ]
        basic_intensity = sum(basic_emotions) / len(basic_emotions)
        
        # Combine both methods (can be adjusted based on preference)
        return (pad_intensity + basic_intensity) / 2.0
    
    def get_emotion_color(self, emotion_name):
        """Get a color representing a specific emotion as (r, g, b) tuple"""
        if emotion_name == "happiness":
            return (1.0, 1.0, 0.0)  # Yellow
        elif emotion_name == "sadness":
            return (0.0, 0.0, 1.0)  # Blue
        elif emotion_name == "anger":
            return (1.0, 0.0, 0.0)  # Red
        elif emotion_name == "fear":
            return (0.5, 0.0, 0.5)  # Purple
        elif emotion_name == "disgust":
            return (0.0, 0.5, 0.0)  # Green
        elif emotion_name == "surprise":
            return (1.0, 0.5, 0.0)  # Orange
        elif emotion_name == "neutral":
            return (0.5, 0.5, 0.5)  # Gray
        else:
            return (1.0, 1.0, 1.0)  # White (default)
    
    def get_dimensions(self):
        """Return a list of emotional dimensions (e.g., PAD)"""
        return self._dimensions


# Factory function to create the appropriate emotion model
def create_emotion_model(model_type="pad_basic", config=None):
    """
    Factory function to create an emotion model based on the specified type.
    
    Args:
        model_type (str): The type of emotion model to create
        config (dict): Configuration parameters for the model
        
    Returns:
        EmotionModel: An instance of the appropriate emotion model
    """
    if model_type == "pad_basic":
        return PADBasicEmotionModel(config)
    else:
        raise ValueError(f"Unknown emotion model type: {model_type}") 