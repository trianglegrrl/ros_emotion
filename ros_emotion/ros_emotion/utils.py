#!/usr/bin/env python3

import yaml
import os
import json
import numpy as np
from builtin_interfaces.msg import Time, Duration
from rclpy.time import Time as rclpy_time
import ament_index_python.packages

def load_config(node, config_file='emotion_config.yaml'):
    """Load configuration from a YAML file."""
    try:
        # Try to find the package share directory
        package_name = 'ros_emotion'
        try:
            package_share_directory = ament_index_python.packages.get_package_share_directory(package_name)
            config_path = os.path.join(package_share_directory, 'config', config_file)
        except Exception:
            # Fallback to local directory
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', config_file)
        
        # If file doesn't exist, try another location
        if not os.path.exists(config_path):
            config_path = os.path.join('/ros_ws/src/ros_emotion/config', config_file)
        
        # If file still doesn't exist, use default values
        if not os.path.exists(config_path):
            node.get_logger().warning(f"ALAINA: Config file not found at {config_path}, using default values")
            return {}
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        node.get_logger().info(f"ALAINA: Loaded configuration from {config_path}")
        return config
    except Exception as e:
        node.get_logger().error(f"ALAINA: Failed to load configuration: {str(e)}")
        return {}

def clamp(value, min_val=-1.0, max_val=1.0):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))

def get_current_time():
    """Get the current time as a ROS Time message."""
    now = rclpy_time().to_msg()
    return now

def create_duration(seconds):
    """Create a ROS Duration message from seconds."""
    duration = Duration()
    duration.sec = int(seconds)
    duration.nanosec = int((seconds - int(seconds)) * 1e9)
    return duration

def json_to_dict(json_str):
    """Convert a JSON string to a Python dictionary."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}

def dict_to_json(data_dict):
    """Convert a Python dictionary to a JSON string."""
    return json.dumps(data_dict)

def calculate_emotion_change(current, target, max_rate):
    """Calculate the change in emotion values with rate limiting."""
    diff = np.array(target) - np.array(current)
    magnitude = np.linalg.norm(diff)
    
    if magnitude > max_rate:
        # Scale the change to respect the maximum rate
        diff = diff * (max_rate / magnitude)
    
    return diff.tolist()

def emotion_decay(value, decay_rate, dt):
    """Apply decay to an emotion value."""
    # Decay towards zero
    if value > 0:
        return max(0.0, value - decay_rate * dt)
    elif value < 0:
        return min(0.0, value + decay_rate * dt)
    return 0.0

def copy_emotional_state(state):
    """
    Create a copy of an EmotionalState message.
    
    Args:
        state: The EmotionalState message to copy
        
    Returns:
        EmotionalState: A new copy of the message
    """
    try:
        # Import the message type
        from ros_emotion.msg import EmotionalState
        
        # Create a new state
        new_state = EmotionalState()
        
        # Copy all fields
        new_state.timestamp = state.timestamp
        new_state.pleasure = state.pleasure
        new_state.arousal = state.arousal
        new_state.dominance = state.dominance
        new_state.happiness = state.happiness
        new_state.sadness = state.sadness
        new_state.anger = state.anger
        new_state.fear = state.fear
        new_state.disgust = state.disgust
        new_state.surprise = state.surprise
        new_state.intensity = state.intensity
        new_state.confidence = state.confidence
        new_state.source = state.source
        new_state.description = state.description
        new_state.primary_emotion = state.primary_emotion
        
        return new_state
    except ImportError:
        # Fall back to a simple dictionary if the message type isn't available
        return state

def copy_emotional_response(response):
    """
    Create a copy of an EmotionalResponse message.
    
    Args:
        response: The EmotionalResponse message to copy
        
    Returns:
        EmotionalResponse: A new copy of the message
    """
    try:
        # Import the message type
        from ros_emotion.msg import EmotionalResponse
        
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
            new_response.previous_state = copy_emotional_state(response.previous_state)
        
        if hasattr(response, 'new_state') and response.new_state:
            new_response.new_state = copy_emotional_state(response.new_state)
        
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