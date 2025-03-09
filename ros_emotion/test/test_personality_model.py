#!/usr/bin/env python3

import unittest
import sys
import os
import numpy as np

# Add the ros_emotion directory to the path so we can import directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules to test
from ros_emotion.personality_model import create_personality_model, PersonalityModel
from ros_emotion.hybrid_personality_model import HybridPersonalityModel
from ros_emotion.msg import EmotionalState, EmotionalResponse


class TestPersonalityModel(unittest.TestCase):
    
    def setUp(self):
        """Setup for the tests"""
        # Create a personality model
        self.personality_model = create_personality_model("hybrid")
        
        # Create a test emotional state
        self.emotional_state = EmotionalState()
        self.emotional_state.pleasure = 0.2
        self.emotional_state.arousal = 0.3
        self.emotional_state.dominance = 0.1
        self.emotional_state.happiness = 0.4
        self.emotional_state.sadness = 0.1
        self.emotional_state.anger = 0.1
        self.emotional_state.fear = 0.2
        self.emotional_state.disgust = 0.1
        self.emotional_state.surprise = 0.3
        self.emotional_state.intensity = 0.5
        
        # Create a test emotional response
        self.emotional_response = EmotionalResponse()
        self.emotional_response.pleasure_delta = 0.2
        self.emotional_response.arousal_delta = 0.1
        self.emotional_response.dominance_delta = 0.3
        self.emotional_response.intensity = 0.6
        self.emotional_response.primary_emotion = "happiness"
    
    def test_traits_initialization(self):
        """Test that traits are initialized properly"""
        # Check that all required traits exist
        traits = self.personality_model.get_all_traits()
        
        # Check for OCEAN traits
        self.assertIn('openness', traits)
        self.assertIn('conscientiousness', traits)
        self.assertIn('extraversion', traits)
        self.assertIn('agreeableness', traits)
        self.assertIn('neuroticism', traits)
        
        # Check default values are within range
        for trait, value in traits.items():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
    
    def test_get_trait_value(self):
        """Test getting trait values"""
        # Test existing trait
        openness = self.personality_model.get_trait_value("openness")
        self.assertIsNotNone(openness)
        self.assertGreaterEqual(openness, 0.0)
        self.assertLessEqual(openness, 1.0)
        
        # Test non-existent trait
        non_existent = self.personality_model.get_trait_value("non_existent_trait")
        self.assertIsNone(non_existent)
    
    def test_set_trait_value(self):
        """Test setting trait values"""
        # Test setting an existing trait
        original_value = self.personality_model.get_trait_value("openness")
        new_value = 0.8
        success = self.personality_model.set_trait_value("openness", new_value)
        
        self.assertTrue(success)
        self.assertEqual(self.personality_model.get_trait_value("openness"), new_value)
        
        # Test setting a non-existent trait
        success = self.personality_model.set_trait_value("non_existent_trait", 0.5)
        self.assertFalse(success)
        
        # Test value clamping
        success = self.personality_model.set_trait_value("openness", 1.5)
        self.assertTrue(success)
        self.assertEqual(self.personality_model.get_trait_value("openness"), 1.0)
        
        success = self.personality_model.set_trait_value("openness", -0.5)
        self.assertTrue(success)
        self.assertEqual(self.personality_model.get_trait_value("openness"), 0.0)
    
    def test_modulate_emotional_response(self):
        """Test modulating emotional responses based on personality"""
        # Test with default traits
        modulated_response = self.personality_model.modulate_emotional_response(
            self.emotional_state, 
            self.emotional_response
        )
        
        # Ensure modulated response is different from original
        self.assertIsNotNone(modulated_response)
        
        # Now test with different personality traits
        # Set high neuroticism (should intensify responses)
        self.personality_model.set_trait_value("neuroticism", 0.9)
        high_neuro_response = self.personality_model.modulate_emotional_response(
            self.emotional_state, 
            self.emotional_response
        )
        
        # Neuroticism should lead to higher intensity
        self.assertGreater(high_neuro_response.intensity, self.emotional_response.intensity)
        
        # Set high agreeableness (should moderate responses)
        self.personality_model.set_trait_value("neuroticism", 0.5)  # Reset
        self.personality_model.set_trait_value("agreeableness", 0.9)
        high_agree_response = self.personality_model.modulate_emotional_response(
            self.emotional_state, 
            self.emotional_response
        )
        
        # Test that modulation maintains valid ranges
        self.assertGreaterEqual(high_agree_response.pleasure_delta, -1.0)
        self.assertLessEqual(high_agree_response.pleasure_delta, 1.0)
        self.assertGreaterEqual(high_agree_response.arousal_delta, -1.0)
        self.assertLessEqual(high_agree_response.arousal_delta, 1.0)
        self.assertGreaterEqual(high_agree_response.dominance_delta, -1.0)
        self.assertLessEqual(high_agree_response.dominance_delta, 1.0)
    
    def test_influence_emotional_state(self):
        """Test personality influence on emotional state"""
        # Test with default traits
        influenced_state = self.personality_model.influence_emotional_state(self.emotional_state)
        
        # Ensure influenced state is not the same object as original
        self.assertIsNot(influenced_state, self.emotional_state)
        
        # Set high extraversion (should increase pleasure and arousal)
        self.personality_model.set_trait_value("extraversion", 0.9)
        high_extravert_state = self.personality_model.influence_emotional_state(self.emotional_state)
        
        # Test that it maintains valid ranges
        self.assertGreaterEqual(high_extravert_state.pleasure, -1.0)
        self.assertLessEqual(high_extravert_state.pleasure, 1.0)
        self.assertGreaterEqual(high_extravert_state.arousal, -1.0)
        self.assertLessEqual(high_extravert_state.arousal, 1.0)
    
    def test_adjust_for_goals(self):
        """Test goal-based adjustments"""
        # Test with default goals
        adjusted_state = self.personality_model.adjust_for_goals(self.emotional_state)
        
        # Ensure adjusted state is not the same object as original
        self.assertIsNot(adjusted_state, self.emotional_state)
        
        # Test with custom goals
        custom_goals = {
            'safety': 0.9,
            'achievement': 0.8
        }
        
        custom_adjusted = self.personality_model.adjust_for_goals(self.emotional_state, custom_goals)
        
        # Test that it maintains valid ranges
        self.assertGreaterEqual(custom_adjusted.pleasure, -1.0)
        self.assertLessEqual(custom_adjusted.pleasure, 1.0)
        self.assertGreaterEqual(custom_adjusted.arousal, -1.0)
        self.assertLessEqual(custom_adjusted.arousal, 1.0)
    
    def test_get_baseline_emotions(self):
        """Test getting baseline emotions"""
        baselines = self.personality_model.get_baseline_emotions()
        
        # Check for all required emotions
        self.assertIn('happiness', baselines)
        self.assertIn('sadness', baselines)
        self.assertIn('anger', baselines)
        self.assertIn('fear', baselines)
        self.assertIn('disgust', baselines)
        self.assertIn('surprise', baselines)
        self.assertIn('pleasure', baselines)
        self.assertIn('arousal', baselines)
        self.assertIn('dominance', baselines)
        
        # Check values are within range
        for emotion, value in baselines.items():
            self.assertGreaterEqual(value, -1.0)
            self.assertLessEqual(value, 1.0)
    
    def test_get_emotional_decay_rates(self):
        """Test getting emotional decay rates"""
        decay_rates = self.personality_model.get_emotional_decay_rates()
        
        # Check for all required emotions
        self.assertIn('happiness', decay_rates)
        self.assertIn('sadness', decay_rates)
        self.assertIn('anger', decay_rates)
        self.assertIn('fear', decay_rates)
        self.assertIn('disgust', decay_rates)
        self.assertIn('surprise', decay_rates)
        self.assertIn('pleasure', decay_rates)
        self.assertIn('arousal', decay_rates)
        self.assertIn('dominance', decay_rates)
        
        # Check values are within range and positive
        for emotion, value in decay_rates.items():
            self.assertGreater(value, 0.0)
            self.assertLessEqual(value, 0.15)
    
    def test_format_personality_traits(self):
        """Test formatting personality traits"""
        formatted = self.personality_model.format_personality_traits()
        
        # Should return a non-empty string
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 0)
        
        # Should include all OCEAN traits
        self.assertIn("Openness", formatted)
        self.assertIn("Conscientiousness", formatted)
        self.assertIn("Extraversion", formatted)
        self.assertIn("Agreeableness", formatted)
        self.assertIn("Neuroticism", formatted)
    
    def test_get_llm_context(self):
        """Test getting LLM context"""
        context = self.personality_model.get_llm_context()
        
        # Should return a non-empty string
        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)
        
        # Context should change based on traits
        self.personality_model.set_trait_value("neuroticism", 0.9)
        high_neuro_context = self.personality_model.get_llm_context()
        
        self.personality_model.set_trait_value("neuroticism", 0.1)
        low_neuro_context = self.personality_model.get_llm_context()
        
        # Contexts should be different
        self.assertNotEqual(high_neuro_context, low_neuro_context)
    
    def test_custom_trait_configuration(self):
        """Test configuring the model with custom traits"""
        custom_config = {
            'traits': {
                'openness': 0.8,
                'conscientiousness': 0.6,
                'extraversion': 0.4,
                'agreeableness': 0.7,
                'neuroticism': 0.2,
                'risk_tolerance': 0.9
            },
            'goals': {
                'safety': 0.3,
                'exploration': 0.8
            }
        }
        
        custom_model = create_personality_model("hybrid", custom_config)
        
        # Check that custom traits were set
        self.assertEqual(custom_model.get_trait_value("openness"), 0.8)
        self.assertEqual(custom_model.get_trait_value("risk_tolerance"), 0.9)
        
        # Check that goals were set
        self.assertEqual(custom_model.goals['safety'], 0.3)
        self.assertEqual(custom_model.goals['exploration'], 0.8)
    
    def test_extreme_personalities(self):
        """Test with extreme personality values"""
        # Create models with extreme personalities
        high_all_config = {
            'traits': {
                'openness': 1.0,
                'conscientiousness': 1.0,
                'extraversion': 1.0,
                'agreeableness': 1.0,
                'neuroticism': 1.0
            }
        }
        
        low_all_config = {
            'traits': {
                'openness': 0.0,
                'conscientiousness': 0.0,
                'extraversion': 0.0,
                'agreeableness': 0.0,
                'neuroticism': 0.0
            }
        }
        
        high_model = create_personality_model("hybrid", high_all_config)
        low_model = create_personality_model("hybrid", low_all_config)
        
        # Test emotional responses with extreme personalities
        high_response = high_model.modulate_emotional_response(
            self.emotional_state, 
            self.emotional_response
        )
        
        low_response = low_model.modulate_emotional_response(
            self.emotional_state, 
            self.emotional_response
        )
        
        # Response intensities should be different
        self.assertNotEqual(high_response.intensity, low_response.intensity)
        
        # Test baseline emotions with extreme personalities
        high_baselines = high_model.get_baseline_emotions()
        low_baselines = low_model.get_baseline_emotions()
        
        # Baseline happiness should be different
        self.assertNotEqual(high_baselines['happiness'], low_baselines['happiness'])


if __name__ == '__main__':
    unittest.main() 