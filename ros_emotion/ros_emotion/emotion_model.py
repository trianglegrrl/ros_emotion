#!/usr/bin/env python3

import numpy as np
from abc import ABC, abstractmethod

# Fix import of custom messages and utils
try:
    # Try ROS message packages first
    from ros_emotion_msgs.msg import EmotionalState
except ImportError:
    # Fall back to local message definition
    from ros_emotion.msg import EmotionalState

# Fix utils import
try:
    from ros_emotion.utils.config_loader import load_config
    from ros_emotion.utils import LLMClient
except ImportError:
    # Fall back to direct imports
    from .utils.config_loader import load_config
    from .utils import LLMClient

import os
import time

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
    
    @abstractmethod
    def format_emotional_state(self, emotional_state):
        """Format the emotional state for display or prompts."""
        pass
    
    @abstractmethod
    def get_emotional_state_color(self, emotional_state):
        """Get a color representing the full emotional state."""
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
        for dimension in self._dimensions:
            self.set_emotion_value(emotional_state, dimension, 0.0)
        
        # Initialize basic emotions
        for emotion in self._basic_emotions:
            self.set_emotion_value(emotional_state, emotion, 0.0)
        
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
            emotion: self.get_emotion_value(emotional_state, emotion)
            for emotion in self._basic_emotions
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
        for dimension in ['pleasure', 'arousal', 'dominance']:
            current_value = self.get_emotion_value(emotional_state, dimension)
            decay_rate = decay_rates.get(dimension, 0.01)  # Default to 0.01 if not specified
            new_value = utils.emotion_decay(current_value, decay_rate, time_diff)
            self.set_emotion_value(emotional_state, dimension, new_value)
        
        # Update basic emotions
        for emotion in ['happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']:
            current_value = self.get_emotion_value(emotional_state, emotion)
            decay_rate = decay_rates.get(emotion, 0.02)  # Default to 0.02 if not specified
            new_value = utils.emotion_decay(current_value, decay_rate, time_diff)
            self.set_emotion_value(emotional_state, emotion, new_value)
        
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
            dimensions = ['pleasure', 'arousal', 'dominance']
            for dimension in dimensions:
                self.set_emotion_value(emotional_state, dimension, utils.clamp(value))
                
            emotions = ['happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']
            for emotion in emotions:
                self.set_emotion_value(emotional_state, emotion, utils.clamp(value, 0.0, 1.0))
            
        elif modification_type == "relative":
            # Adjust all emotions by the specified value
            dimensions = ['pleasure', 'arousal', 'dominance']
            for dimension in dimensions:
                current = self.get_emotion_value(emotional_state, dimension)
                self.set_emotion_value(emotional_state, dimension, utils.clamp(current + value))
                
            emotions = ['happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']
            for emotion in emotions:
                current = self.get_emotion_value(emotional_state, emotion)
                self.set_emotion_value(emotional_state, emotion, utils.clamp(current + value, 0.0, 1.0))
            
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
        pad_intensity = (
            abs(self.get_emotion_value(emotional_state, "pleasure")) + 
            abs(self.get_emotion_value(emotional_state, "arousal")) + 
            abs(self.get_emotion_value(emotional_state, "dominance"))
        ) / 3.0
        
        # Method 2: Average of basic emotions
        basic_emotions_values = [
            self.get_emotion_value(emotional_state, emotion)
            for emotion in self._basic_emotions
        ]
        basic_intensity = sum(basic_emotions_values) / len(basic_emotions_values)
        
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
    
    def format_emotional_state(self, emotional_state):
        """Format the emotional state for display or prompts."""
        # Format dimensions section
        dimensions_text = "Dimensional Model:\n"
        for dim in self._dimensions:
            value = self.get_emotion_value(emotional_state, dim)
            dimensions_text += f"- {dim.capitalize()}: {value:.2f} (-1.0 to 1.0)\n"
        
        # Format basic emotions section
        emotions_text = "\nBasic Emotions:\n"
        for emotion in self._basic_emotions:
            value = self.get_emotion_value(emotional_state, emotion)
            emotions_text += f"- {emotion.capitalize()}: {value:.2f} (0.0 to 1.0)\n"
        
        # Calculate intensity
        intensity = self.calculate_intensity(emotional_state)
        
        return f"""
{dimensions_text}
{emotions_text}
Overall Intensity: {intensity:.2f}
Primary Emotion: {emotional_state.primary_emotion}
Description: {emotional_state.description}
"""
    
    def get_emotional_state_color(self, emotional_state):
        """Get a color representing the full emotional state."""
        # Get values from the emotion state
        pleasure = self.get_emotion_value(emotional_state, "pleasure")
        arousal = self.get_emotion_value(emotional_state, "arousal")  
        dominance = self.get_emotion_value(emotional_state, "dominance")
        intensity = self.calculate_intensity(emotional_state)
        
        # Red component based on pleasure (negative = more red)
        r = 0.5 - pleasure * 0.5
        
        # Green component based on arousal (positive = more green)
        g = 0.5 + arousal * 0.5
        
        # Blue component based on dominance (positive = more blue)
        b = 0.5 + dominance * 0.5
        
        # Alpha based on intensity (not used in standard RGB tuples)
        a = 1.0
        
        return (r, g, b)


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