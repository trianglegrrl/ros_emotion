#!/usr/bin/env python3

import numpy as np
import json
try:
    # For running as a ROS node
    import ros_emotion.utils as utils
    from ros_emotion.msg import EmotionalState, EmotionalResponse
    from ros_emotion.personality_model import PersonalityModel
except ImportError:
    # For testing within the package
    from . import utils
    from ..msg import EmotionalState, EmotionalResponse
    from .personality_model import PersonalityModel

class HybridPersonalityModel(PersonalityModel):
    """
    Concrete implementation of a hybrid personality model combining the Five-Factor Model
    (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism)
    with goal-oriented behavior adjustments.
    """
    
    def __init__(self, config=None):
        """
        Initialize the hybrid personality model.
        
        Args:
            config: Configuration dictionary for personality traits
        """
        # Initialize with default values
        self.traits = {
            # Five Factor Model (OCEAN)
            'openness': 0.5,      # Openness to experience
            'conscientiousness': 0.5,  # Conscientiousness
            'extraversion': 0.5,  # Extraversion
            'agreeableness': 0.5, # Agreeableness
            'neuroticism': 0.5,   # Neuroticism (emotional instability)
            
            # Additional traits that can be extended
            'risk_tolerance': 0.5,  # Tolerance for risky situations
            'adaptability': 0.5,    # Ability to adapt to changing situations
            'creativity': 0.5,      # Creative problem-solving
            'resilience': 0.5       # Emotional resilience
        }
        
        # Goals and their current importance (0.0 to 1.0)
        self.goals = {
            'safety': 0.7,        # Safety and security
            'social': 0.5,        # Social interaction
            'achievement': 0.6,   # Task achievement
            'exploration': 0.4,   # Exploration and learning
            'stability': 0.6      # Emotional stability
        }
        
        # Trait-emotion influence matrices
        # How each trait influences baseline emotions
        self.trait_emotion_influence = {
            'openness': {
                'happiness': 0.2,
                'sadness': -0.1,
                'anger': -0.1,
                'fear': -0.3,
                'disgust': -0.2,
                'surprise': 0.4
            },
            'conscientiousness': {
                'happiness': 0.1,
                'sadness': -0.1,
                'anger': -0.2,
                'fear': -0.1,
                'disgust': 0.1,
                'surprise': -0.1
            },
            'extraversion': {
                'happiness': 0.4,
                'sadness': -0.3,
                'anger': 0.1,
                'fear': -0.3,
                'disgust': -0.1,
                'surprise': 0.2
            },
            'agreeableness': {
                'happiness': 0.3,
                'sadness': 0.0,
                'anger': -0.4,
                'fear': -0.1,
                'disgust': -0.3,
                'surprise': 0.0
            },
            'neuroticism': {
                'happiness': -0.4,
                'sadness': 0.4,
                'anger': 0.3,
                'fear': 0.4,
                'disgust': 0.2,
                'surprise': 0.1
            }
        }
        
        # How each trait influences emotion decay rates
        self.trait_decay_influence = {
            'openness': {
                'happiness': -0.1,
                'sadness': -0.2,
                'anger': -0.1,
                'fear': -0.3,
                'disgust': -0.2,
                'surprise': -0.3
            },
            'conscientiousness': {
                'happiness': 0.0,
                'sadness': 0.2,
                'anger': 0.3,
                'fear': 0.1,
                'disgust': 0.1,
                'surprise': 0.2
            },
            'extraversion': {
                'happiness': -0.2,
                'sadness': 0.3,
                'anger': 0.2,
                'fear': 0.3,
                'disgust': 0.2,
                'surprise': 0.1
            },
            'agreeableness': {
                'happiness': -0.1,
                'sadness': 0.1,
                'anger': 0.4,
                'fear': 0.2,
                'disgust': 0.3,
                'surprise': 0.1
            },
            'neuroticism': {
                'happiness': 0.3,
                'sadness': -0.3,
                'anger': -0.3,
                'fear': -0.4,
                'disgust': -0.2,
                'surprise': -0.1
            }
        }
        
        # How each trait influences PAD dimensions
        self.trait_dimension_influence = {
            'openness': {
                'pleasure': 0.2,
                'arousal': 0.1,
                'dominance': 0.2
            },
            'conscientiousness': {
                'pleasure': 0.1,
                'arousal': -0.1,
                'dominance': 0.3
            },
            'extraversion': {
                'pleasure': 0.3,
                'arousal': 0.4,
                'dominance': 0.3
            },
            'agreeableness': {
                'pleasure': 0.3,
                'arousal': -0.2,
                'dominance': -0.3
            },
            'neuroticism': {
                'pleasure': -0.4,
                'arousal': 0.3,
                'dominance': -0.3
            }
        }
        
        # Default baseline decay rates
        self.default_decay_rates = {
            'happiness': 0.05,
            'sadness': 0.03,
            'anger': 0.04,
            'fear': 0.04,
            'disgust': 0.03,
            'surprise': 0.08,
            'pleasure': 0.05,
            'arousal': 0.04,
            'dominance': 0.03
        }
        
        # Override with provided config
        if config:
            self.initialize_traits(config)
            
        # Log initialization
        self._log_info("Initialized HybridPersonalityModel")
        self._log_debug(f"Initial traits: {self.format_personality_traits()}")
    
    def _log_info(self, message):
        """Log info message with proper ALAINA format"""
        try:
            import rclpy
            import logging
            if rclpy.ok():
                import rclpy.logging
                logger = rclpy.logging.get_logger('personality_model')
                logger.info(f"ALAINA: {message}")
            else:
                print(f"INFO: ALAINA: {message}")
        except ImportError:
            print(f"INFO: ALAINA: {message}")
    
    def _log_debug(self, message):
        """Log debug message with proper ALAINA format"""
        try:
            import rclpy
            if rclpy.ok():
                import rclpy.logging
                logger = rclpy.logging.get_logger('personality_model')
                logger.debug(f"ALAINA: {message}")
            else:
                print(f"DEBUG: ALAINA: {message}")
        except ImportError:
            print(f"DEBUG: ALAINA: {message}")
    
    def initialize_traits(self, config=None):
        """
        Initialize or update personality traits from configuration.
        
        Args:
            config: Configuration dictionary for personality traits
        """
        if not config:
            self._log_info("No configuration provided, using default traits")
            return
            
        # Update traits from config
        for trait, value in config.get('traits', {}).items():
            if trait in self.traits:
                self.traits[trait] = utils.clamp(value, 0.0, 1.0)
        
        # Update goals from config
        for goal, value in config.get('goals', {}).items():
            self.goals[goal] = utils.clamp(value, 0.0, 1.0)
        
        # Update influence matrices if provided
        if 'trait_emotion_influence' in config:
            for trait, influences in config['trait_emotion_influence'].items():
                if trait in self.trait_emotion_influence:
                    self.trait_emotion_influence[trait].update(influences)
        
        if 'trait_decay_influence' in config:
            for trait, influences in config['trait_decay_influence'].items():
                if trait in self.trait_decay_influence:
                    self.trait_decay_influence[trait].update(influences)
        
        if 'trait_dimension_influence' in config:
            for trait, influences in config['trait_dimension_influence'].items():
                if trait in self.trait_dimension_influence:
                    self.trait_dimension_influence[trait].update(influences)
        
        # Update default decay rates if provided
        if 'default_decay_rates' in config:
            self.default_decay_rates.update(config['default_decay_rates'])
            
        self._log_info("Initialized traits from configuration")
        self._log_debug(f"Updated traits: {self.format_personality_traits()}")
    
    def get_all_traits(self):
        """
        Get all personality traits in the model.
        
        Returns:
            dict: A dictionary of all traits and their values
        """
        return self.traits.copy()
    
    def get_trait_value(self, trait_name):
        """
        Get the value of a specific personality trait.
        
        Args:
            trait_name: Name of the trait to get
            
        Returns:
            float: The value of the trait (0.0 to 1.0), or None if not found
        """
        return self.traits.get(trait_name, None)
    
    def set_trait_value(self, trait_name, value):
        """
        Set the value of a specific personality trait.
        
        Args:
            trait_name: Name of the trait to set
            value: New value for the trait
            
        Returns:
            bool: True if successful, False otherwise
        """
        if trait_name in self.traits:
            self.traits[trait_name] = utils.clamp(value, 0.0, 1.0)
            self._log_info(f"Set trait {trait_name} to {self.traits[trait_name]}")
            return True
        return False
    
    def modulate_emotional_response(self, emotional_state, emotional_response):
        """
        Modulate an emotional response based on personality traits.
        
        Args:
            emotional_state: Current emotional state
            emotional_response: Proposed emotional response
            
        Returns:
            EmotionalResponse: The modulated emotional response
        """
        # Clone the response to avoid modifying the original
        modulated_response = utils.copy_emotional_response(emotional_response)
        
        # Adjust delta values based on personality traits
        personality_factor = self._calculate_personality_response_factor()
        
        # Apply personality-based modulation to emotion deltas
        modulated_response.pleasure_delta *= personality_factor.get('pleasure', 1.0)
        modulated_response.arousal_delta *= personality_factor.get('arousal', 1.0)
        modulated_response.dominance_delta *= personality_factor.get('dominance', 1.0)
        
        # Adjust intensity based on personality (e.g., high neuroticism = higher intensity)
        intensity_factor = 1.0 + (self.traits['neuroticism'] - 0.5) * 0.4
        modulated_response.intensity *= intensity_factor
        
        # Add personality context to the response metadata
        try:
            metadata = json.loads(modulated_response.metadata) if modulated_response.metadata else {}
        except json.JSONDecodeError:
            metadata = {}
        
        metadata['personality_influence'] = {
            'factor': personality_factor,
            'intensity_adjustment': intensity_factor,
            'primary_trait_influence': self._get_primary_trait_influence()
        }
        modulated_response.metadata = json.dumps(metadata)
        
        # Logging
        self._log_debug(f"Modulated emotional response with intensity factor: {intensity_factor}")
        
        return modulated_response
    
    def _calculate_personality_response_factor(self):
        """
        Calculate personality-based response factors.
        
        Returns:
            dict: Factors for each emotional dimension
        """
        # Calculate response factors based on personality traits
        factors = {
            'pleasure': 1.0,
            'arousal': 1.0,
            'dominance': 1.0
        }
        
        # Apply trait influences on response factors
        for trait, value in self.traits.items():
            trait_norm = value - 0.5  # Normalize around 0 (-0.5 to 0.5)
            
            if trait in self.trait_dimension_influence:
                for dimension, influence in self.trait_dimension_influence[trait].items():
                    if dimension in factors:
                        # Apply the influence proportional to trait value
                        factors[dimension] += trait_norm * influence
        
        # Ensure reasonable bounds
        for dim in factors:
            factors[dim] = utils.clamp(factors[dim], 0.5, 1.5)
            
        return factors
    
    def _get_primary_trait_influence(self):
        """
        Get the trait with the strongest current influence.
        
        Returns:
            str: Name of the primary influential trait
        """
        # Find the trait furthest from neutral (0.5)
        primary_trait = max(self.traits.items(), key=lambda x: abs(x[1] - 0.5))
        return primary_trait[0]
    
    def influence_emotional_state(self, emotional_state):
        """
        Apply personality influence to the emotional state.
        
        Args:
            emotional_state: Current emotional state
            
        Returns:
            EmotionalState: The influenced emotional state
        """
        # Clone the state to avoid modifying the original
        influenced_state = utils.copy_emotional_state(emotional_state)
        
        # Get baseline emotion adjustments from personality
        baseline_adjustments = self._calculate_baseline_emotion_adjustments()
        
        # Apply personality-based adjustments to emotional dimensions
        influenced_state.pleasure = utils.clamp(
            influenced_state.pleasure + baseline_adjustments.get('pleasure', 0.0)
        )
        influenced_state.arousal = utils.clamp(
            influenced_state.arousal + baseline_adjustments.get('arousal', 0.0)
        )
        influenced_state.dominance = utils.clamp(
            influenced_state.dominance + baseline_adjustments.get('dominance', 0.0)
        )
        
        # Apply personality-based adjustments to basic emotions
        influenced_state.happiness = utils.clamp(
            influenced_state.happiness + baseline_adjustments.get('happiness', 0.0)
        )
        influenced_state.sadness = utils.clamp(
            influenced_state.sadness + baseline_adjustments.get('sadness', 0.0)
        )
        influenced_state.anger = utils.clamp(
            influenced_state.anger + baseline_adjustments.get('anger', 0.0)
        )
        influenced_state.fear = utils.clamp(
            influenced_state.fear + baseline_adjustments.get('fear', 0.0)
        )
        influenced_state.disgust = utils.clamp(
            influenced_state.disgust + baseline_adjustments.get('disgust', 0.0)
        )
        influenced_state.surprise = utils.clamp(
            influenced_state.surprise + baseline_adjustments.get('surprise', 0.0)
        )
        
        # Update intensity and description
        influenced_state.intensity = self.calculate_intensity(influenced_state)
        influenced_state.primary_emotion = self._determine_primary_emotion(influenced_state)
        
        # Update description to include personality influence
        personality_info = f"Personality traits ({self._get_primary_trait_influence()} dominant) "
        personality_info += f"influence this emotional state."
        
        if influenced_state.description:
            influenced_state.description = f"{influenced_state.description} {personality_info}"
        else:
            influenced_state.description = personality_info
            
        self._log_debug(f"Applied personality influence to emotional state")
        
        return influenced_state
    
    def _calculate_baseline_emotion_adjustments(self):
        """
        Calculate baseline emotion adjustments based on personality.
        
        Returns:
            dict: Adjustments for each emotion and dimension
        """
        adjustments = {
            'pleasure': 0.0,
            'arousal': 0.0,
            'dominance': 0.0,
            'happiness': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'disgust': 0.0,
            'surprise': 0.0
        }
        
        # Small adjustments based on traits
        for trait, value in self.traits.items():
            trait_norm = value - 0.5  # Normalize around 0 (-0.5 to 0.5)
            
            # Apply dimension influences
            if trait in self.trait_dimension_influence:
                for dimension, influence in self.trait_dimension_influence[trait].items():
                    if dimension in adjustments:
                        # Small adjustment proportional to trait value
                        adjustments[dimension] += trait_norm * influence * 0.1
            
            # Apply emotion influences
            if trait in self.trait_emotion_influence:
                for emotion, influence in self.trait_emotion_influence[trait].items():
                    if emotion in adjustments:
                        # Small adjustment proportional to trait value
                        adjustments[emotion] += trait_norm * influence * 0.1
        
        return adjustments
    
    def _determine_primary_emotion(self, emotional_state):
        """
        Determine the primary emotion in the emotional state.
        
        Args:
            emotional_state: The emotional state to analyze
            
        Returns:
            str: The name of the primary emotion
        """
        # Get emotion values
        emotions = {
            'happiness': emotional_state.happiness,
            'sadness': emotional_state.sadness,
            'anger': emotional_state.anger,
            'fear': emotional_state.fear,
            'disgust': emotional_state.disgust,
            'surprise': emotional_state.surprise
        }
        
        # Find the emotion with the highest value
        primary_emotion = max(emotions.items(), key=lambda x: x[1])
        return primary_emotion[0]
    
    def adjust_for_goals(self, emotional_state, goals=None):
        """
        Adjust emotional state based on current goals and personality.
        
        Args:
            emotional_state: Current emotional state
            goals: Dictionary of current goals and their importance (optional)
            
        Returns:
            EmotionalState: The adjusted emotional state
        """
        # Use provided goals or the default ones
        active_goals = goals if goals is not None else self.goals
        
        # Clone the state to avoid modifying the original
        adjusted_state = utils.copy_emotional_state(emotional_state)
        
        # Calculate goal-based adjustments
        goal_adjustments = self._calculate_goal_adjustments(active_goals)
        
        # Apply goal-based adjustments to dimensions
        adjusted_state.pleasure = utils.clamp(
            adjusted_state.pleasure + goal_adjustments.get('pleasure', 0.0)
        )
        adjusted_state.arousal = utils.clamp(
            adjusted_state.arousal + goal_adjustments.get('arousal', 0.0)
        )
        adjusted_state.dominance = utils.clamp(
            adjusted_state.dominance + goal_adjustments.get('dominance', 0.0)
        )
        
        # Apply goal-based adjustments to emotions
        adjusted_state.happiness = utils.clamp(
            adjusted_state.happiness + goal_adjustments.get('happiness', 0.0)
        )
        adjusted_state.sadness = utils.clamp(
            adjusted_state.sadness + goal_adjustments.get('sadness', 0.0)
        )
        adjusted_state.anger = utils.clamp(
            adjusted_state.anger + goal_adjustments.get('anger', 0.0)
        )
        adjusted_state.fear = utils.clamp(
            adjusted_state.fear + goal_adjustments.get('fear', 0.0)
        )
        adjusted_state.disgust = utils.clamp(
            adjusted_state.disgust + goal_adjustments.get('disgust', 0.0)
        )
        adjusted_state.surprise = utils.clamp(
            adjusted_state.surprise + goal_adjustments.get('surprise', 0.0)
        )
        
        # Update intensity and primary emotion
        adjusted_state.intensity = self.calculate_intensity(adjusted_state)
        adjusted_state.primary_emotion = self._determine_primary_emotion(adjusted_state)
        
        # Update description
        if adjusted_state.description:
            adjusted_state.description = f"{adjusted_state.description} (Adjusted for goals.)"
        else:
            adjusted_state.description = "Emotional state adjusted for current goals."
            
        self._log_debug(f"Adjusted emotional state for goals: {', '.join([f'{g}:{v:.2f}' for g, v in active_goals.items()])}")
        
        return adjusted_state
    
    def _calculate_goal_adjustments(self, goals):
        """
        Calculate goal-based adjustments to emotions.
        
        Args:
            goals: Dictionary of current goals and their importance
            
        Returns:
            dict: Adjustments for each emotion and dimension
        """
        adjustments = {
            'pleasure': 0.0,
            'arousal': 0.0,
            'dominance': 0.0,
            'happiness': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'disgust': 0.0,
            'surprise': 0.0
        }
        
        # Goal-specific influences on emotions and dimensions
        goal_influences = {
            'safety': {
                'fear': -0.2,
                'arousal': -0.1,
                'dominance': 0.2
            },
            'social': {
                'happiness': 0.2,
                'pleasure': 0.1,
                'arousal': 0.1
            },
            'achievement': {
                'happiness': 0.1,
                'dominance': 0.2,
                'pleasure': 0.1
            },
            'exploration': {
                'surprise': 0.2,
                'arousal': 0.2,
                'pleasure': 0.1
            },
            'stability': {
                'arousal': -0.2,
                'fear': -0.1,
                'anger': -0.1,
                'sadness': -0.1
            }
        }
        
        # Apply each goal's influence weighted by importance and personality
        for goal, importance in goals.items():
            if goal in goal_influences and importance > 0:
                # Modify influence based on personality
                personality_modifier = self._get_goal_personality_modifier(goal)
                
                # Apply influences
                for aspect, influence in goal_influences[goal].items():
                    if aspect in adjustments:
                        # Small adjustment based on goal importance and personality
                        adjusted_influence = influence * importance * personality_modifier
                        adjustments[aspect] += adjusted_influence * 0.1
        
        return adjustments
    
    def _get_goal_personality_modifier(self, goal):
        """
        Get personality-based modifier for a specific goal.
        
        Args:
            goal: The goal to get a modifier for
            
        Returns:
            float: Modifier value (0.5 to 1.5)
        """
        # Different goals are enhanced by different personality traits
        goal_trait_mappings = {
            'safety': ['conscientiousness', 'neuroticism'],
            'social': ['extraversion', 'agreeableness'],
            'achievement': ['conscientiousness', 'extraversion'],
            'exploration': ['openness', 'extraversion'],
            'stability': ['conscientiousness', 'agreeableness']
        }
        
        modifier = 1.0
        
        if goal in goal_trait_mappings:
            # Average the relevant trait values
            relevant_traits = goal_trait_mappings[goal]
            trait_values = [self.traits.get(trait, 0.5) for trait in relevant_traits]
            avg_trait_value = sum(trait_values) / len(trait_values)
            
            # Map from 0-1 range to 0.5-1.5 range
            modifier = 0.5 + avg_trait_value
        
        return modifier
    
    def get_baseline_emotions(self):
        """
        Get baseline emotion values influenced by personality.
        
        Returns:
            dict: Dictionary of baseline emotion values
        """
        baselines = {
            'happiness': 0.1,
            'sadness': 0.1,
            'anger': 0.1,
            'fear': 0.1,
            'disgust': 0.1,
            'surprise': 0.1,
            'pleasure': 0.0,
            'arousal': 0.0,
            'dominance': 0.0
        }
        
        # Apply personality influences to baselines
        for trait, value in self.traits.items():
            trait_norm = value - 0.5  # Normalize around 0 (-0.5 to 0.5)
            
            # Apply dimension influences
            if trait in self.trait_dimension_influence:
                for dimension, influence in self.trait_dimension_influence[trait].items():
                    if dimension in baselines:
                        baselines[dimension] += trait_norm * influence * 0.2
            
            # Apply emotion influences
            if trait in self.trait_emotion_influence:
                for emotion, influence in self.trait_emotion_influence[trait].items():
                    if emotion in baselines:
                        baselines[emotion] += trait_norm * influence * 0.2
        
        # Ensure all values are within proper range
        for emotion in baselines:
            baselines[emotion] = utils.clamp(baselines[emotion])
        
        self._log_debug(f"Calculated personality-influenced baseline emotions")
        
        return baselines
    
    def get_emotional_decay_rates(self):
        """
        Get emotional decay rates influenced by personality.
        
        Returns:
            dict: Dictionary of emotion decay rates
        """
        # Start with default decay rates
        decay_rates = self.default_decay_rates.copy()
        
        # Apply personality influences to decay rates
        for trait, value in self.traits.items():
            trait_norm = value - 0.5  # Normalize around 0 (-0.5 to 0.5)
            
            if trait in self.trait_decay_influence:
                for emotion, influence in self.trait_decay_influence[trait].items():
                    if emotion in decay_rates:
                        # Adjust decay rate based on trait
                        # Positive influence = faster decay, negative = slower decay
                        decay_rates[emotion] *= (1.0 + trait_norm * influence * 0.3)
        
        # Ensure reasonable bounds for decay rates
        for emotion in decay_rates:
            decay_rates[emotion] = utils.clamp(decay_rates[emotion], 0.01, 0.15)
        
        self._log_debug(f"Calculated personality-influenced decay rates")
        
        return decay_rates
    
    def calculate_intensity(self, emotional_state):
        """
        Calculate the overall intensity of an emotional state.
        
        Args:
            emotional_state: The emotional state to analyze
            
        Returns:
            float: The overall intensity (0.0 to 1.0)
        """
        # Basic emotions contribution
        emotion_values = [
            emotional_state.happiness,
            emotional_state.sadness,
            emotional_state.anger,
            emotional_state.fear,
            emotional_state.disgust,
            emotional_state.surprise
        ]
        
        # PAD dimensions contribution
        dimension_values = [
            abs(emotional_state.pleasure),
            abs(emotional_state.arousal),
            abs(emotional_state.dominance)
        ]
        
        # Calculate intensity - more weight to the highest emotion
        max_emotion = max(emotion_values)
        avg_emotion = sum(emotion_values) / len(emotion_values)
        avg_dimension = sum(dimension_values) / len(dimension_values)
        
        # Combine with weights
        intensity = max_emotion * 0.5 + avg_emotion * 0.25 + avg_dimension * 0.25
        
        # Personality influence (e.g., neuroticism increases intensity)
        neuroticism_factor = 1.0 + (self.traits['neuroticism'] - 0.5) * 0.4
        extraversion_factor = 1.0 + (self.traits['extraversion'] - 0.5) * 0.2
        
        # Apply personality factors
        intensity *= neuroticism_factor * extraversion_factor
        
        # Ensure within bounds
        intensity = utils.clamp(intensity)
        
        return intensity
    
    def format_personality_traits(self):
        """
        Format personality traits for human-readable output.
        
        Returns:
            str: Human-readable description of personality traits
        """
        # Format each trait with a descriptive term
        trait_descriptions = []
        
        trait_terms = {
            'openness': ['conservative', 'moderate', 'curious', 'exploratory', 'innovative'],
            'conscientiousness': ['spontaneous', 'flexible', 'balanced', 'organized', 'disciplined'],
            'extraversion': ['introverted', 'reserved', 'ambivert', 'outgoing', 'extraverted'],
            'agreeableness': ['challenging', 'questioning', 'neutral', 'cooperative', 'harmonious'],
            'neuroticism': ['stable', 'calm', 'average', 'reactive', 'sensitive']
        }
        
        # Convert trait values to descriptive terms
        for trait, terms in trait_terms.items():
            if trait in self.traits:
                # Map trait value to term index (0.0-0.2 -> 0, 0.2-0.4 -> 1, etc.)
                value = self.traits[trait]
                term_index = min(int(value * 5), 4)
                description = f"{trait.capitalize()}: {terms[term_index]} ({value:.2f})"
                trait_descriptions.append(description)
        
        # Add secondary traits
        secondary_traits = [t for t in self.traits if t not in trait_terms]
        for trait in secondary_traits:
            value = self.traits[trait]
            description = f"{trait.capitalize()}: {value:.2f}"
            trait_descriptions.append(description)
        
        # Format the full description
        return " | ".join(trait_descriptions)
    
    def get_llm_context(self):
        """
        Get personality context for LLM integration.
        
        Returns:
            str: Description of personality for LLM prompts
        """
        # Generate descriptions for each of the main traits
        trait_descriptions = []
        
        # OCEAN model descriptors
        if self.traits['openness'] > 0.7:
            trait_descriptions.append("highly open to new experiences and ideas")
        elif self.traits['openness'] < 0.3:
            trait_descriptions.append("preferring familiar routines and conventional approaches")
        
        if self.traits['conscientiousness'] > 0.7:
            trait_descriptions.append("very conscientious and detail-oriented")
        elif self.traits['conscientiousness'] < 0.3:
            trait_descriptions.append("spontaneous and flexible rather than structured")
        
        if self.traits['extraversion'] > 0.7:
            trait_descriptions.append("strongly extraverted and socially energetic")
        elif self.traits['extraversion'] < 0.3:
            trait_descriptions.append("introverted and preferring solitary activities")
        
        if self.traits['agreeableness'] > 0.7:
            trait_descriptions.append("highly agreeable and cooperative")
        elif self.traits['agreeableness'] < 0.3:
            trait_descriptions.append("direct and straightforward in interactions")
        
        if self.traits['neuroticism'] > 0.7:
            trait_descriptions.append("emotionally sensitive and reactive")
        elif self.traits['neuroticism'] < 0.3:
            trait_descriptions.append("emotionally stable and calm under pressure")
        
        # Build the personality description
        description = "This personality is characterized as "
        
        if trait_descriptions:
            description += ", ".join(trait_descriptions)
        else:
            description += "having a balanced personality profile"
        
        # Add information about primary traits
        primary_traits = sorted(
            [(trait, abs(value - 0.5)) for trait, value in self.traits.items()],
            key=lambda x: x[1],
            reverse=True
        )[:2]  # Top 2 most extreme traits
        
        if primary_traits and primary_traits[0][1] > 0.15:  # Only if there's a significant deviation
            primary_trait = primary_traits[0][0]
            value = self.traits[primary_trait]
            description += f". The most defining trait is {primary_trait} "
            description += "which is high" if value > 0.5 else "which is low"
        
        # Add goal information
        important_goals = sorted(
            [(goal, value) for goal, value in self.goals.items()],
            key=lambda x: x[1],
            reverse=True
        )[:2]  # Top 2 most important goals
        
        if important_goals and important_goals[0][1] > 0.6:  # Only if there's an important goal
            description += f". Currently prioritizing {important_goals[0][0]}"
            if len(important_goals) > 1 and important_goals[1][1] > 0.5:
                description += f" and {important_goals[1][0]}"
        
        return description

def utils_copy_emotional_response(response):
    """
    Create a copy of an EmotionalResponse message.
    
    Args:
        response: The EmotionalResponse message to copy
        
    Returns:
        EmotionalResponse: A new copy of the message
    """
    try:
        # Import the message type
        from ros_emotion.msg import EmotionalResponse, EmotionalState
        
        # Create a new response
        new_response = EmotionalResponse()
        
        # Copy all fields
        new_response.timestamp = response.timestamp
        new_response.stimulus_id = response.stimulus_id
        new_response.is_rumination = response.is_rumination
        new_response.response_text = response.response_text
        new_response.source = response.source
        
        # Copy emotional states
        if hasattr(response, 'previous_state') and response.previous_state:
            new_response.previous_state = utils.copy_emotional_state(response.previous_state)
        
        if hasattr(response, 'new_state') and response.new_state:
            new_response.new_state = utils.copy_emotional_state(response.new_state)
        
        # Copy other fields
        new_response.pleasure_delta = response.pleasure_delta
        new_response.arousal_delta = response.arousal_delta
        new_response.dominance_delta = response.dominance_delta
        new_response.primary_emotion = response.primary_emotion
        new_response.intensity = response.intensity
        new_response.confidence = response.confidence
        new_response.metadata = response.metadata
        
        return new_response
    except ImportError:
        # Fall back to a simple dictionary if the message type isn't available
        return response

# Add the copy_emotional_response function to utils if it doesn't exist
if not hasattr(utils, 'copy_emotional_response'):
    utils.copy_emotional_response = utils_copy_emotional_response 