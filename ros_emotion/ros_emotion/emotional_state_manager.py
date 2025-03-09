#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import EmotionalState, SensoryInput, RuminationUpdate
from ros_emotion.srv import EmotionQuery, EmotionModify
import numpy as np
import uuid
import ros_emotion.utils as utils

class EmotionalStateManager(Node):
    def __init__(self):
        super().__init__('emotional_state_manager')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.manager_config = self.config.get('emotional_state_manager', {})
        
        # Initialize emotional state
        self.emotional_state = EmotionalState()
        self.initialize_emotional_state()
        
        # Create publishers
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        self.state_publisher = self.create_publisher(
            EmotionalState, 
            'emotional_state', 
            qos
        )
        
        # Create subscribers
        self.sensory_input_sub = self.create_subscription(
            SensoryInput,
            'sensory_input',
            self.sensory_input_callback,
            qos
        )
        
        self.rumination_update_sub = self.create_subscription(
            RuminationUpdate,
            'rumination_update',
            self.rumination_update_callback,
            qos
        )
        
        # Create services
        self.query_service = self.create_service(
            EmotionQuery,
            'query_emotional_state',
            self.query_emotional_state
        )
        
        self.modify_service = self.create_service(
            EmotionModify,
            'modify_emotional_state',
            self.modify_emotional_state
        )
        
        # Create timer for regular updates
        update_frequency = self.manager_config.get('update_frequency', 10.0)
        self.update_timer = self.create_timer(
            1.0 / update_frequency,
            self.update_emotional_state
        )
        
        # Track last update time for decay calculations
        self.last_update_time = self.get_clock().now()
        
        self.get_logger().info("ALAINA: Emotional State Manager initialized")
    
    def initialize_emotional_state(self):
        """Initialize the emotional state with default values."""
        initial_state = self.manager_config.get('initial_state', {})
        
        self.emotional_state.timestamp = utils.get_current_time()
        self.emotional_state.pleasure = initial_state.get('pleasure', 0.0)
        self.emotional_state.arousal = initial_state.get('arousal', 0.0)
        self.emotional_state.dominance = initial_state.get('dominance', 0.0)
        self.emotional_state.happiness = initial_state.get('happiness', 0.0)
        self.emotional_state.sadness = initial_state.get('sadness', 0.0)
        self.emotional_state.anger = initial_state.get('anger', 0.0)
        self.emotional_state.fear = initial_state.get('fear', 0.0)
        self.emotional_state.disgust = initial_state.get('disgust', 0.0)
        self.emotional_state.surprise = initial_state.get('surprise', 0.0)
        self.emotional_state.intensity = initial_state.get('intensity', 0.0)
        self.emotional_state.confidence = initial_state.get('confidence', 1.0)
        self.emotional_state.source = "initialization"
        self.emotional_state.description = "Initial emotional state"
        
        # Initialize the primary emotion
        self.update_primary_emotion()
        
        self.get_logger().info("ALAINA: Emotional state initialized")
    
    def update_emotional_state(self):
        """Update the emotional state (apply decay, etc.)."""
        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds / 1e9  # Convert to seconds
        self.last_update_time = now
        
        # Apply decay to emotional dimensions
        decay_rates = self.manager_config.get('decay_rates', {})
        threshold = self.manager_config.get('threshold', 0.05)
        
        # Apply decay to each dimension
        self.emotional_state.pleasure = utils.emotion_decay(
            self.emotional_state.pleasure, 
            decay_rates.get('pleasure', 0.01), 
            dt
        )
        
        self.emotional_state.arousal = utils.emotion_decay(
            self.emotional_state.arousal, 
            decay_rates.get('arousal', 0.02), 
            dt
        )
        
        self.emotional_state.dominance = utils.emotion_decay(
            self.emotional_state.dominance, 
            decay_rates.get('dominance', 0.005), 
            dt
        )
        
        # Apply decay to basic emotions
        self.emotional_state.happiness = utils.emotion_decay(
            self.emotional_state.happiness, 
            decay_rates.get('happiness', 0.02), 
            dt
        )
        
        self.emotional_state.sadness = utils.emotion_decay(
            self.emotional_state.sadness, 
            decay_rates.get('sadness', 0.01), 
            dt
        )
        
        self.emotional_state.anger = utils.emotion_decay(
            self.emotional_state.anger, 
            decay_rates.get('anger', 0.03), 
            dt
        )
        
        self.emotional_state.fear = utils.emotion_decay(
            self.emotional_state.fear, 
            decay_rates.get('fear', 0.02), 
            dt
        )
        
        self.emotional_state.disgust = utils.emotion_decay(
            self.emotional_state.disgust, 
            decay_rates.get('disgust', 0.01), 
            dt
        )
        
        self.emotional_state.surprise = utils.emotion_decay(
            self.emotional_state.surprise, 
            decay_rates.get('surprise', 0.04), 
            dt
        )
        
        # Calculate overall emotional intensity
        self.emotional_state.intensity = min(1.0, max(
            abs(self.emotional_state.pleasure),
            abs(self.emotional_state.arousal),
            abs(self.emotional_state.dominance),
            self.emotional_state.happiness,
            self.emotional_state.sadness,
            self.emotional_state.anger,
            self.emotional_state.fear,
            self.emotional_state.disgust,
            self.emotional_state.surprise
        ))
        
        # Update the primary emotion based on the highest emotion value
        self.update_primary_emotion()
        
        # Update the timestamp
        self.emotional_state.timestamp = utils.get_current_time()
        self.emotional_state.source = "decay_update"
        
        # Publish updated state
        self.state_publisher.publish(self.emotional_state)
    
    def sensory_input_callback(self, msg):
        """Process incoming sensory input."""
        self.get_logger().info(f"ALAINA: Received sensory input: {msg.description}")
        
        # In a real implementation, this would process the sensory input
        # and update the emotional state accordingly.
        # For now, we'll just log it and let the LLM integration handle it.
        
        # Update the source of the emotional state
        self.emotional_state.source = f"sensory_input:{msg.input_type}"
    
    def rumination_update_callback(self, msg):
        """Process rumination updates."""
        self.get_logger().info(f"ALAINA: Received rumination update: {msg.description}")
        
        # Apply changes from rumination
        max_rate = self.manager_config.get('max_rate_of_change', 0.2)
        
        # Update dimensional model
        self.emotional_state.pleasure = utils.clamp(
            self.emotional_state.pleasure + msg.pleasure_change
        )
        self.emotional_state.arousal = utils.clamp(
            self.emotional_state.arousal + msg.arousal_change
        )
        self.emotional_state.dominance = utils.clamp(
            self.emotional_state.dominance + msg.dominance_change
        )
        
        # Update basic emotions
        self.emotional_state.happiness = utils.clamp(
            self.emotional_state.happiness + msg.happiness_change, 0.0, 1.0
        )
        self.emotional_state.sadness = utils.clamp(
            self.emotional_state.sadness + msg.sadness_change, 0.0, 1.0
        )
        self.emotional_state.anger = utils.clamp(
            self.emotional_state.anger + msg.anger_change, 0.0, 1.0
        )
        self.emotional_state.fear = utils.clamp(
            self.emotional_state.fear + msg.fear_change, 0.0, 1.0
        )
        self.emotional_state.disgust = utils.clamp(
            self.emotional_state.disgust + msg.disgust_change, 0.0, 1.0
        )
        self.emotional_state.surprise = utils.clamp(
            self.emotional_state.surprise + msg.surprise_change, 0.0, 1.0
        )
        
        # Update source and description
        self.emotional_state.source = f"rumination:{msg.original_input_id}"
        if msg.description:
            self.emotional_state.description = msg.description
        
        # Update timestamp
        self.emotional_state.timestamp = utils.get_current_time()
        
        # Publish updated state
        self.state_publisher.publish(self.emotional_state)
    
    def query_emotional_state(self, request, response):
        """Service to query the current emotional state."""
        self.get_logger().info(f"ALAINA: Emotional state query: {request.query_type}")
        
        response.success = True
        response.error_message = ""
        
        # Copy the current emotional state
        response.emotional_state = self.emotional_state
        
        # If not requesting full state, clear fields based on query type
        if request.query_type == "dimensional":
            # Clear categorical emotions
            response.emotional_state.happiness = 0.0
            response.emotional_state.sadness = 0.0
            response.emotional_state.anger = 0.0
            response.emotional_state.fear = 0.0
            response.emotional_state.disgust = 0.0
            response.emotional_state.surprise = 0.0
        
        elif request.query_type == "categorical":
            # Clear dimensional model
            response.emotional_state.pleasure = 0.0
            response.emotional_state.arousal = 0.0
            response.emotional_state.dominance = 0.0
        
        elif request.query_type == "specific":
            # Return only the specific emotion
            specific = request.specific_emotion.lower()
            
            # Clear all emotions first
            temp_state = EmotionalState()
            temp_state.timestamp = self.emotional_state.timestamp
            temp_state.intensity = self.emotional_state.intensity
            temp_state.confidence = self.emotional_state.confidence
            temp_state.source = self.emotional_state.source
            
            # Set only the requested emotion
            if specific == "pleasure":
                temp_state.pleasure = self.emotional_state.pleasure
            elif specific == "arousal":
                temp_state.arousal = self.emotional_state.arousal
            elif specific == "dominance":
                temp_state.dominance = self.emotional_state.dominance
            elif specific == "happiness":
                temp_state.happiness = self.emotional_state.happiness
            elif specific == "sadness":
                temp_state.sadness = self.emotional_state.sadness
            elif specific == "anger":
                temp_state.anger = self.emotional_state.anger
            elif specific == "fear":
                temp_state.fear = self.emotional_state.fear
            elif specific == "disgust":
                temp_state.disgust = self.emotional_state.disgust
            elif specific == "surprise":
                temp_state.surprise = self.emotional_state.surprise
            else:
                response.success = False
                response.error_message = f"Unknown emotion: {specific}"
            
            if response.success:
                response.emotional_state = temp_state
        
        # Clear description if not requested
        if not request.include_description:
            response.emotional_state.description = ""
        
        return response
    
    def modify_emotional_state(self, request, response):
        """Service to modify the current emotional state."""
        self.get_logger().info(f"ALAINA: Emotional state modification: {request.modification_type}")
        
        response.success = True
        response.error_message = ""
        
        # Handle different modification types
        if request.modification_type == "reset":
            # Reset to initial state
            self.initialize_emotional_state()
            self.emotional_state.source = "reset"
            self.emotional_state.description = f"Reset due to: {request.reason}"
        
        elif request.modification_type == "absolute":
            # Set all emotions to the specified value
            self.emotional_state.pleasure = utils.clamp(request.value)
            self.emotional_state.arousal = utils.clamp(request.value)
            self.emotional_state.dominance = utils.clamp(request.value)
            self.emotional_state.happiness = utils.clamp(request.value, 0.0, 1.0)
            self.emotional_state.sadness = utils.clamp(request.value, 0.0, 1.0)
            self.emotional_state.anger = utils.clamp(request.value, 0.0, 1.0)
            self.emotional_state.fear = utils.clamp(request.value, 0.0, 1.0)
            self.emotional_state.disgust = utils.clamp(request.value, 0.0, 1.0)
            self.emotional_state.surprise = utils.clamp(request.value, 0.0, 1.0)
            self.emotional_state.source = "absolute_modification"
            self.emotional_state.description = f"Absolute modification due to: {request.reason}"
        
        elif request.modification_type == "relative":
            # Adjust all emotions by the specified value
            self.emotional_state.pleasure = utils.clamp(self.emotional_state.pleasure + request.value)
            self.emotional_state.arousal = utils.clamp(self.emotional_state.arousal + request.value)
            self.emotional_state.dominance = utils.clamp(self.emotional_state.dominance + request.value)
            self.emotional_state.happiness = utils.clamp(self.emotional_state.happiness + request.value, 0.0, 1.0)
            self.emotional_state.sadness = utils.clamp(self.emotional_state.sadness + request.value, 0.0, 1.0)
            self.emotional_state.anger = utils.clamp(self.emotional_state.anger + request.value, 0.0, 1.0)
            self.emotional_state.fear = utils.clamp(self.emotional_state.fear + request.value, 0.0, 1.0)
            self.emotional_state.disgust = utils.clamp(self.emotional_state.disgust + request.value, 0.0, 1.0)
            self.emotional_state.surprise = utils.clamp(self.emotional_state.surprise + request.value, 0.0, 1.0)
            self.emotional_state.source = "relative_modification"
            self.emotional_state.description = f"Relative modification due to: {request.reason}"
        
        elif request.modification_type == "specific":
            # Modify only the specific emotion
            specific = request.specific_emotion.lower()
            
            if specific == "pleasure":
                self.emotional_state.pleasure = utils.clamp(request.value)
            elif specific == "arousal":
                self.emotional_state.arousal = utils.clamp(request.value)
            elif specific == "dominance":
                self.emotional_state.dominance = utils.clamp(request.value)
            elif specific == "happiness":
                self.emotional_state.happiness = utils.clamp(request.value, 0.0, 1.0)
            elif specific == "sadness":
                self.emotional_state.sadness = utils.clamp(request.value, 0.0, 1.0)
            elif specific == "anger":
                self.emotional_state.anger = utils.clamp(request.value, 0.0, 1.0)
            elif specific == "fear":
                self.emotional_state.fear = utils.clamp(request.value, 0.0, 1.0)
            elif specific == "disgust":
                self.emotional_state.disgust = utils.clamp(request.value, 0.0, 1.0)
            elif specific == "surprise":
                self.emotional_state.surprise = utils.clamp(request.value, 0.0, 1.0)
            else:
                response.success = False
                response.error_message = f"Unknown emotion: {specific}"
            
            if response.success:
                self.emotional_state.source = f"specific_modification:{specific}"
                self.emotional_state.description = f"Modified {specific} due to: {request.reason}"
        
        else:
            response.success = False
            response.error_message = f"Unknown modification type: {request.modification_type}"
        
        # Update timestamp
        self.emotional_state.timestamp = utils.get_current_time()
        
        # Calculate overall intensity
        basic_emotions = [
            self.emotional_state.happiness,
            self.emotional_state.sadness,
            self.emotional_state.anger,
            self.emotional_state.fear,
            self.emotional_state.disgust,
            self.emotional_state.surprise
        ]
        self.emotional_state.intensity = sum(abs(e) for e in basic_emotions) / len(basic_emotions)
        
        # Update the primary emotion based on the modified state
        self.update_primary_emotion()
        
        # Publish updated state
        if response.success:
            self.state_publisher.publish(self.emotional_state)
        
        # Set response
        response.updated_emotional_state = self.emotional_state
        
        return response

    def update_primary_emotion(self):
        """Update the primary_emotion field based on the highest emotional value."""
        emotions = {
            "happiness": self.emotional_state.happiness,
            "sadness": self.emotional_state.sadness,
            "anger": self.emotional_state.anger,
            "fear": self.emotional_state.fear,
            "disgust": self.emotional_state.disgust,
            "surprise": self.emotional_state.surprise
        }
        
        # Find the emotion with the highest value
        primary_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        
        # If all emotions are below threshold, set to neutral
        threshold = self.manager_config.get('threshold', 0.05)
        if emotions[primary_emotion] < threshold:
            primary_emotion = "neutral"
        
        self.emotional_state.primary_emotion = primary_emotion
        self.get_logger().info(f"ALAINA: Primary emotion updated to: {primary_emotion}")

def main(args=None):
    rclpy.init(args=args)
    node = EmotionalStateManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("ALAINA: Keyboard interrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 