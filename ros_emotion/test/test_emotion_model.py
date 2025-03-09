#!/usr/bin/env python3

import unittest
import rclpy
from ros_emotion.msg import EmotionalState
from ros_emotion.emotion_model import create_emotion_model, PADBasicEmotionModel, EmotionModel

import numpy as np

class TestEmotionModel(unittest.TestCase):
    """Test cases for the EmotionModel class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Initialize ROS context if not already done
        if not rclpy.ok():
            rclpy.init()
        
        # Create an instance of the emotion model
        self.model = create_emotion_model()
        
        # Config for testing
        self.test_config = {
            'threshold': 0.1
        }
        self.model_with_config = create_emotion_model(config=self.test_config)
    
    def tearDown(self):
        """Tear down test fixtures"""
        pass
    
    def test_create_emotional_state(self):
        """Test creating a new emotional state"""
        state = self.model.create_emotional_state()
        
        # Check that it's an EmotionalState message
        self.assertIsInstance(state, EmotionalState)
        
        # Check that all emotion values are initialized to 0
        self.assertEqual(state.pleasure, 0.0)
        self.assertEqual(state.arousal, 0.0)
        self.assertEqual(state.dominance, 0.0)
        self.assertEqual(state.happiness, 0.0)
        self.assertEqual(state.sadness, 0.0)
        self.assertEqual(state.anger, 0.0)
        self.assertEqual(state.fear, 0.0)
        self.assertEqual(state.disgust, 0.0)
        self.assertEqual(state.surprise, 0.0)
        
        # Check that the primary emotion is neutral
        self.assertEqual(state.primary_emotion, "neutral")
    
    def test_get_primary_emotion(self):
        """Test getting the primary emotion"""
        state = self.model.create_emotional_state()
        
        # All emotions at 0, should be neutral
        self.assertEqual(self.model.get_primary_emotion(state), "neutral")
        
        # Set happiness to be the highest
        state.happiness = 0.5
        self.assertEqual(self.model.get_primary_emotion(state), "happiness")
        
        # Set anger higher
        state.anger = 0.7
        self.assertEqual(self.model.get_primary_emotion(state), "anger")
        
        # Set sadness highest
        state.sadness = 0.8
        state.anger = 0.3
        self.assertEqual(self.model.get_primary_emotion(state), "sadness")
        
        # Test with different threshold
        state = self.model.create_emotional_state()
        state.happiness = 0.08  # Below default threshold of 0.05 for the regular model
        self.assertEqual(self.model.get_primary_emotion(state), "happiness")
        self.assertEqual(self.model_with_config.get_primary_emotion(state), "neutral")  # Should be neutral with 0.1 threshold
    
    def test_update_state(self):
        """Test updating the emotional state with decay"""
        state = self.model.create_emotional_state()
        
        # Set some initial values
        state.pleasure = 0.5
        state.arousal = 0.5
        state.happiness = 0.5
        
        # Create decay rates
        decay_rates = {
            'pleasure': 0.1,
            'arousal': 0.2,
            'happiness': 0.3
        }
        
        # Update with a 1 second time diff
        updated_state = self.model.update_state(state, 1.0, decay_rates)
        
        # Check that values decayed correctly
        self.assertAlmostEqual(updated_state.pleasure, 0.4, places=5)  # 0.5 - 0.1*1.0
        self.assertAlmostEqual(updated_state.arousal, 0.3, places=5)   # 0.5 - 0.2*1.0
        self.assertAlmostEqual(updated_state.happiness, 0.2, places=5) # 0.5 - 0.3*1.0
    
    def test_modify_state(self):
        """Test modifying the emotional state"""
        state = self.model.create_emotional_state()
        
        # Test absolute modification
        modified_state = self.model.modify_state(state, "absolute", 0.5)
        self.assertEqual(modified_state.pleasure, 0.5)
        self.assertEqual(modified_state.arousal, 0.5)
        self.assertEqual(modified_state.happiness, 0.5)
        
        # Test relative modification
        state = self.model.create_emotional_state()
        state.pleasure = 0.3
        modified_state = self.model.modify_state(state, "relative", 0.2)
        self.assertEqual(modified_state.pleasure, 0.5)  # 0.3 + 0.2
        
        # Test specific modification
        state = self.model.create_emotional_state()
        modified_state = self.model.modify_state(state, "specific", 0.7, "fear")
        self.assertEqual(modified_state.fear, 0.7)
        self.assertEqual(modified_state.happiness, 0.0)  # Should be unchanged
        
        # Test reset
        state = self.model.create_emotional_state()
        state.pleasure = 0.5
        state.arousal = 0.5
        state.happiness = 0.5
        state.source = "test"
        state.description = "test description"
        
        reset_state = self.model.modify_state(state, "reset", 0.0)
        self.assertEqual(reset_state.pleasure, 0.0)
        self.assertEqual(reset_state.arousal, 0.0)
        self.assertEqual(reset_state.happiness, 0.0)
        self.assertEqual(reset_state.source, "test")  # Should preserve source
        self.assertEqual(reset_state.description, "test description")  # Should preserve description
    
    def test_get_all_emotions(self):
        """Test getting all emotions"""
        emotions = self.model.get_all_emotions()
        
        expected_emotions = ["happiness", "sadness", "anger", "fear", "disgust", "surprise"]
        self.assertEqual(sorted(emotions), sorted(expected_emotions))
    
    def test_get_emotion_value(self):
        """Test getting emotion values"""
        state = self.model.create_emotional_state()
        state.pleasure = 0.5
        state.happiness = 0.7
        
        self.assertEqual(self.model.get_emotion_value(state, "pleasure"), 0.5)
        self.assertEqual(self.model.get_emotion_value(state, "happiness"), 0.7)
        
        # Test invalid emotion
        with self.assertRaises(ValueError):
            self.model.get_emotion_value(state, "invalid_emotion")
    
    def test_set_emotion_value(self):
        """Test setting emotion values"""
        state = self.model.create_emotional_state()
        
        # Set valid emotions
        self.model.set_emotion_value(state, "pleasure", 0.5)
        self.model.set_emotion_value(state, "happiness", 0.7)
        
        self.assertEqual(state.pleasure, 0.5)
        self.assertEqual(state.happiness, 0.7)
        
        # Test invalid emotion
        with self.assertRaises(ValueError):
            self.model.set_emotion_value(state, "invalid_emotion", 0.5)
    
    def test_calculate_intensity(self):
        """Test calculating intensity"""
        state = self.model.create_emotional_state()
        
        # All zeros should give zero intensity
        self.assertEqual(self.model.calculate_intensity(state), 0.0)
        
        # Set some values
        state.pleasure = 0.5
        state.arousal = 0.5
        state.dominance = 0.5
        state.happiness = 0.5
        
        # Test that intensity is calculated
        intensity = self.model.calculate_intensity(state)
        self.assertGreater(intensity, 0.0)
    
    def test_get_emotion_color(self):
        """Test getting emotion colors"""
        # Test a few emotions
        self.assertEqual(self.model.get_emotion_color("happiness"), (1.0, 1.0, 0.0))
        self.assertEqual(self.model.get_emotion_color("anger"), (1.0, 0.0, 0.0))
        self.assertEqual(self.model.get_emotion_color("neutral"), (0.5, 0.5, 0.5))
        
        # Test invalid emotion (should return default)
        self.assertEqual(self.model.get_emotion_color("invalid_emotion"), (1.0, 1.0, 1.0))
    
    def test_get_dimensions(self):
        """Test getting dimensions"""
        dimensions = self.model.get_dimensions()
        
        expected_dimensions = ["pleasure", "arousal", "dominance"]
        self.assertEqual(sorted(dimensions), sorted(expected_dimensions))
    
    def test_factory_function(self):
        """Test the factory function"""
        # Test creating default model
        model = create_emotion_model()
        self.assertIsInstance(model, PADBasicEmotionModel)
        
        # Test creating model with config
        model = create_emotion_model(config=self.test_config)
        self.assertIsInstance(model, PADBasicEmotionModel)
        self.assertEqual(model.threshold, 0.1)
        
        # Test invalid model type
        with self.assertRaises(ValueError):
            create_emotion_model("invalid_model_type")


if __name__ == '__main__':
    unittest.main() 