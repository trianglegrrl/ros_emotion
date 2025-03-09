#!/usr/bin/env python3

from abc import ABC, abstractmethod
import numpy as np
try:
    # For running as a ROS node
    import ros_emotion.utils as utils
    from ros_emotion.msg import EmotionalState, EmotionalResponse
except ImportError:
    # For testing within the package
    from . import utils
    from ..msg import EmotionalState, EmotionalResponse

class PersonalityModel(ABC):
    """
    Abstract base class for personality models.
    This provides a common interface for different personality models that can be used
    to influence emotional processing in the system.
    """
    
    @abstractmethod
    def initialize_traits(self, config=None):
        """
        Initialize the personality traits based on configuration.
        
        Args:
            config: Configuration dictionary for personality traits
        """
        pass
    
    @abstractmethod
    def get_all_traits(self):
        """
        Get all personality traits in the model.
        
        Returns:
            dict: A dictionary of all traits and their values
        """
        pass
    
    @abstractmethod
    def get_trait_value(self, trait_name):
        """
        Get the value of a specific personality trait.
        
        Args:
            trait_name: Name of the trait to get
            
        Returns:
            float: The value of the trait (typically normalized between 0.0 and 1.0)
        """
        pass
    
    @abstractmethod
    def set_trait_value(self, trait_name, value):
        """
        Set the value of a specific personality trait.
        
        Args:
            trait_name: Name of the trait to set
            value: New value for the trait
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def modulate_emotional_response(self, emotional_state, emotional_response):
        """
        Modulate an emotional response based on personality traits.
        
        Args:
            emotional_state: Current emotional state
            emotional_response: Proposed emotional response
            
        Returns:
            EmotionalResponse: The modulated emotional response
        """
        pass
    
    @abstractmethod
    def influence_emotional_state(self, emotional_state):
        """
        Apply personality influence to the emotional state.
        
        Args:
            emotional_state: Current emotional state
            
        Returns:
            EmotionalState: The influenced emotional state
        """
        pass
    
    @abstractmethod
    def adjust_for_goals(self, emotional_state, goals):
        """
        Adjust emotional state based on current goals and personality.
        
        Args:
            emotional_state: Current emotional state
            goals: Dictionary of current goals and their importance
            
        Returns:
            EmotionalState: The adjusted emotional state
        """
        pass
    
    @abstractmethod
    def get_baseline_emotions(self):
        """
        Get baseline emotion values influenced by personality.
        
        Returns:
            dict: Dictionary of baseline emotion values
        """
        pass
    
    @abstractmethod
    def get_emotional_decay_rates(self):
        """
        Get emotional decay rates influenced by personality.
        
        Returns:
            dict: Dictionary of emotion decay rates
        """
        pass
    
    @abstractmethod
    def format_personality_traits(self):
        """
        Format personality traits for human-readable output.
        
        Returns:
            str: Human-readable description of personality traits
        """
        pass
    
    @abstractmethod
    def get_llm_context(self):
        """
        Get personality context for LLM integration.
        
        Returns:
            str: Description of personality for LLM prompts
        """
        pass


def create_personality_model(model_type="hybrid", config=None):
    """
    Factory function to create a personality model of the specified type.
    
    Args:
        model_type (str): Type of personality model to create
        config (dict): Configuration for the personality model
        
    Returns:
        PersonalityModel: An initialized personality model
    """
    if model_type == "hybrid":
        from ros_emotion.hybrid_personality_model import HybridPersonalityModel
        return HybridPersonalityModel(config)
    else:
        raise ValueError(f"Unknown personality model type: {model_type}") 