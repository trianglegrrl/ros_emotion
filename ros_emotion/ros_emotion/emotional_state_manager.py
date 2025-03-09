#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import EmotionalState, SensoryInput, RuminationUpdate
from ros_emotion.srv import EmotionQuery, EmotionModify
import numpy as np
import uuid
import json
import ros_emotion.utils as utils
# Import our emotion model
from ros_emotion.emotion_model import create_emotion_model, EmotionModel, PADBasicEmotionModel
# Import our personality model
from ros_emotion.personality_model import create_personality_model, PersonalityModel
import os

class EmotionalStateManager(Node):
    def __init__(self):
        super().__init__('emotional_state_manager')
        
        # Load configuration
        self.manager_config = utils.load_config(self, 'emotion_config.yaml').get('emotional_state_manager', {})
        
        # Create the emotional state object
        self.emotional_state = EmotionalState()
        
        # Initialize the emotion model
        emotion_model_type = self.manager_config.get('emotion_model_type', 'pad_basic')
        self.emotion_model = create_emotion_model(emotion_model_type)
        
        # Initialize the personality model
        personality_model_type = self.manager_config.get('personality_model_type', 'hybrid')
        personality_config = self.manager_config.get('personality', {})
        self.personality_model = create_personality_model(personality_model_type, personality_config)
        
        self.initialize_emotional_state()
        
        # Initialize tracking variables
        self.last_update_time = self.get_clock().now()
        self.count = 0  # For logging frequency control
        
        # Define QoS profile for reliable communication
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Publisher for emotional state
        self.state_publisher = self.create_publisher(
            EmotionalState,
            'emotional_state',
            10
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
        
        # Create timer for less frequent personality influence
        personality_update_frequency = self.manager_config.get('personality_update_frequency', 1.0)
        self.personality_timer = self.create_timer(
            1.0 / personality_update_frequency,
            self.apply_personality_influence
        )
        
        self.get_logger().info("ALAINA: Emotional State Manager initialized")
        self.get_logger().info(f"ALAINA: Using personality model: {personality_model_type}")
        self.get_logger().debug(f"ALAINA: Personality traits: {self.personality_model.format_personality_traits()}")
    
    def initialize_emotional_state(self):
        """Initialize the emotional state with default values."""
        # Create a new emotional state using the emotion model
        self.emotional_state = self.emotion_model.create_emotional_state()
        
        # Override any values specified in config
        initial_state = self.manager_config.get('initial_state', {})
        
        # Define which fields are emotions vs. metadata
        emotion_dimensions = self.emotion_model.get_dimensions()
        basic_emotions = self.emotion_model.get_all_emotions()
        valid_emotions = emotion_dimensions + basic_emotions
        
        # Apply any custom initial values from config
        for field, value in initial_state.items():
            if field in valid_emotions:
                # For valid emotions, use the emotion model interface
                self.emotion_model.set_emotion_value(
                    self.emotional_state, 
                    field, 
                    value
                )
            elif field == "intensity":
                self.emotional_state.intensity = value
            elif field == "confidence":
                self.emotional_state.confidence = value
            elif field == "source":
                self.emotional_state.source = value
            elif field == "description":
                self.emotional_state.description = value
            elif field == "primary_emotion":
                self.emotional_state.primary_emotion = value
        
        # Set default values for required fields if not already set
        if not self.emotional_state.source:
            self.emotional_state.source = "initialization"
        if not self.emotional_state.description:
            self.emotional_state.description = "Initial emotional state"
        
        # Apply personality influence to baseline emotions
        self.apply_personality_baseline()
        
        # Update the primary emotion
        self.update_primary_emotion()
        
        self.get_logger().info("ALAINA: Emotional state initialized")
    
    def apply_personality_baseline(self):
        """Apply personality baseline influences to the emotional state."""
        # Get personality-influenced baseline values
        baseline_emotions = self.personality_model.get_baseline_emotions()
        
        # Apply baseline adjustments for emotions
        for emotion, baseline in baseline_emotions.items():
            if emotion in self.emotion_model.get_all_emotions() or emotion in self.emotion_model.get_dimensions():
                current = self.emotion_model.get_emotion_value(self.emotional_state, emotion)
                # Only apply if the current value is close to neutral
                if abs(current) < 0.15:
                    self.emotion_model.set_emotion_value(self.emotional_state, emotion, baseline)
        
        self.get_logger().debug("ALAINA: Applied personality baseline to emotional state")
    
    def apply_personality_influence(self):
        """Apply personality influence to the current emotional state."""
        # Apply personality influence to the emotional state
        influenced_state = self.personality_model.influence_emotional_state(self.emotional_state)
        
        # Check if there are active goals that should influence the state
        goals = self.manager_config.get('active_goals', {})
        if goals:
            # Apply goal adjustments based on personality
            influenced_state = self.personality_model.adjust_for_goals(influenced_state, goals)
            self.get_logger().debug(f"ALAINA: Applied goal adjustments with {len(goals)} active goals")
        
        # Update the emotional state
        self.emotional_state = influenced_state
        
        # Update timestamp
        self.emotional_state.timestamp = utils.get_current_time()
        
        # Update primary emotion
        self.update_primary_emotion()
        
        # Add personality info to metadata
        metadata = {}
        try:
            if self.emotional_state.description and "{" in self.emotional_state.description:
                # Extract existing metadata if it's embedded in the description
                start = self.emotional_state.description.find("{")
                end = self.emotional_state.description.rfind("}") + 1
                if start > 0 and end > start:
                    metadata_str = self.emotional_state.description[start:end]
                    try:
                        metadata = json.loads(metadata_str)
                        # Remove the metadata from the description
                        self.emotional_state.description = self.emotional_state.description[:start].strip()
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self.get_logger().warn(f"ALAINA: Error extracting metadata: {e}")
        
        # Add personality information to metadata
        metadata['personality_traits'] = {
            k: v for k, v in self.personality_model.get_all_traits().items() 
            if k in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
        }
        
        # Add primary trait influence
        primary_trait = max(
            metadata['personality_traits'].items(), 
            key=lambda x: abs(x[1] - 0.5)
        )[0]
        metadata['primary_trait'] = primary_trait
        
        # Embed the metadata in the description
        if not self.emotional_state.description.endswith("."):
            self.emotional_state.description += "."
        
        self.emotional_state.description += f" Influenced by {primary_trait}."
        
        # Publish updated state
        self.state_publisher.publish(self.emotional_state)
        
        self.get_logger().debug("ALAINA: Applied personality influence to emotional state")
    
    def update_emotional_state(self):
        """Update the emotional state based on decay rates and publish the current state."""
        # Get the current time
        current_time = self.get_clock().now()
        
        # Calculate time difference in seconds
        time_diff = (current_time - self.last_update_time).nanoseconds / 1e9
        self.last_update_time = current_time
        
        # Get personality-influenced decay rates
        decay_rates = self.personality_model.get_emotional_decay_rates()
        
        # Use the emotion model to update the state
        self.emotion_model.update_state(self.emotional_state, time_diff, decay_rates)
        
        # Update timestamp
        self.emotional_state.timestamp = utils.get_current_time()
        
        # Update primary emotion
        self.update_primary_emotion()
        
        # Ensure primary emotion is set before publishing
        if not hasattr(self.emotional_state, 'primary_emotion') or not self.emotional_state.primary_emotion:
            self.update_primary_emotion()
            self.get_logger().warn("ALAINA: Had to set primary_emotion before publishing")
            
        # Publish current state
        self.state_publisher.publish(self.emotional_state)
        
        # Debug log
        if self.count % 10 == 0:  # only log every 10th update to reduce spam
            # Use emotion model to get dimension values
            dimensions = self.emotion_model.get_dimensions()
            dimension_str = ", ".join([f"{dim[0].upper()}{dim[1:]}={self.emotion_model.get_emotion_value(self.emotional_state, dim):.2f}" for dim in dimensions])
            
            self.get_logger().info(
                f"ALAINA: Emotional state: {dimension_str}, " +
                f"Primary={self.emotional_state.primary_emotion}"
            )
            
        self.count += 1
    
    def sensory_input_callback(self, msg):
        """Process incoming sensory input."""
        self.get_logger().info(f"ALAINA: Received sensory input: {msg.description}")
        
        # In a real implementation, this would process the sensory input
        # and update the emotional state accordingly.
        # For now, we'll just log it and let the LLM integration handle it.
        
        # Update the source of the emotional state
        self.emotional_state.source = f"sensory_input:{msg.input_type}"
        
        # Trigger personality influence after receiving input
        self.apply_personality_influence()
    
    def rumination_update_callback(self, msg):
        """Process rumination updates."""
        self.get_logger().info(f"ALAINA: Received rumination update: {msg.description}")
        
        # Apply changes from rumination using emotion model
        
        # Update the emotional state fields according to the rumination changes
        if hasattr(msg, 'pleasure_change') and msg.pleasure_change != 0.0:
            current_val = self.emotion_model.get_emotion_value(self.emotional_state, "pleasure")
            self.emotion_model.set_emotion_value(
                self.emotional_state,
                "pleasure",
                current_val + msg.pleasure_change
            )
            
        if hasattr(msg, 'arousal_change') and msg.arousal_change != 0.0:
            current_val = self.emotion_model.get_emotion_value(self.emotional_state, "arousal")
            self.emotion_model.set_emotion_value(
                self.emotional_state,
                "arousal",
                current_val + msg.arousal_change
            )
            
        if hasattr(msg, 'dominance_change') and msg.dominance_change != 0.0:
            current_val = self.emotion_model.get_emotion_value(self.emotional_state, "dominance")
            self.emotion_model.set_emotion_value(
                self.emotional_state,
                "dominance",
                current_val + msg.dominance_change
            )
            
        # Update basic emotions
        for emotion in ['happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']:
            change_field = f"{emotion}_change"
            if hasattr(msg, change_field) and getattr(msg, change_field) != 0.0:
                current_val = self.emotion_model.get_emotion_value(self.emotional_state, emotion)
                self.emotion_model.set_emotion_value(
                    self.emotional_state,
                    emotion,
                    current_val + getattr(msg, change_field)
                )
        
        # Update source and description
        self.emotional_state.source = f"rumination:{msg.original_input_id}"
        if msg.description:
            self.emotional_state.description = msg.description
        
        # Update timestamp
        self.emotional_state.timestamp = utils.get_current_time()
        
        # Apply personality influence to the rumination response
        self.apply_personality_influence()
        
        # Update primary emotion
        self.update_primary_emotion()
        
        # Publish updated state
        self.state_publisher.publish(self.emotional_state)
    
    def query_emotional_state(self, request, response):
        """Service to query the current emotional state."""
        self.get_logger().info(f"ALAINA: Emotional state query: {request.query_type}")
        
        response.success = True
        response.error_message = ""
        
        # Copy the current emotional state
        response.emotional_state = utils.copy_emotional_state(self.emotional_state)
        
        # If not requesting full state, clear fields based on query type
        if request.query_type == "dimensional":
            # Clear categorical emotions using emotion model
            for emotion in ['happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']:
                self.emotion_model.set_emotion_value(response.emotional_state, emotion, 0.0)
        
        elif request.query_type == "categorical":
            # Clear dimensional model using emotion model
            for dimension in ['pleasure', 'arousal', 'dominance']:
                self.emotion_model.set_emotion_value(response.emotional_state, dimension, 0.0)
        
        elif request.query_type == "specific":
            # Return only the specific emotion
            specific = request.specific_emotion.lower()
            
            # Create a new state with only the specific emotion
            temp_state = EmotionalState()
            temp_state.timestamp = self.emotional_state.timestamp
            temp_state.intensity = self.emotional_state.intensity
            temp_state.confidence = self.emotional_state.confidence
            temp_state.source = self.emotional_state.source
            temp_state.primary_emotion = ""  # Will be updated based on remaining values
            
            # Check if specific is a personality trait
            if specific.startswith("personality."):
                trait_name = specific.split('.')[1]
                trait_value = self.personality_model.get_trait_value(trait_name)
                
                if trait_value is not None:
                    # Return information about the personality trait
                    temp_state.description = f"{trait_name.capitalize()}: {trait_value:.2f}"
                    temp_state.intensity = trait_value
                    temp_state.primary_emotion = trait_name
                    response.emotional_state = temp_state
                else:
                    response.success = False
                    response.error_message = f"Unknown personality trait: {trait_name}"
            
            # Standard emotion query
            elif specific in ['pleasure', 'arousal', 'dominance', 
                           'happiness', 'sadness', 'anger', 
                           'fear', 'disgust', 'surprise']:
                # Copy the specific emotion value
                value = self.emotion_model.get_emotion_value(self.emotional_state, specific)
                self.emotion_model.set_emotion_value(temp_state, specific, value)
                response.emotional_state = temp_state
            else:
                response.success = False
                response.error_message = f"Unknown emotion: {specific}"
        
        # Add personality information to the response if requested
        if request.include_description:
            # Add personality context to the description
            personality_info = f"Personality: {self.personality_model.format_personality_traits()}"
            if response.emotional_state.description:
                response.emotional_state.description += f" {personality_info}"
            else:
                response.emotional_state.description = personality_info
        else:
            response.emotional_state.description = ""
        
        return response
    
    def modify_emotional_state(self, request, response):
        """Service to modify the current emotional state."""
        self.get_logger().info(f"ALAINA: Emotional state modification request: {request.modification_type}")
        
        response.success = True
        response.error_message = ""
        
        # Save original state in case we need to revert
        original_state = utils.copy_emotional_state(self.emotional_state)
        
        # Store reason and source before modification
        reason = request.reason if request.reason else "External modification"
        source = f"{request.modification_type}_modification"
        
        try:
            # Check if this is a personality trait modification
            if request.modification_type == "personality_trait":
                # Modify a personality trait
                if not request.specific_emotion:
                    raise ValueError("Personality trait modification requires a specific trait name")
                
                # Set the trait value
                success = self.personality_model.set_trait_value(
                    request.specific_emotion,
                    request.value
                )
                
                if not success:
                    raise ValueError(f"Failed to set personality trait: {request.specific_emotion}")
                
                # Apply personality influence after trait change
                self.apply_personality_influence()
                
                # Update description
                self.emotional_state.description = f"Personality trait {request.specific_emotion} modified due to: {reason}"
                self.emotional_state.source = "personality_modification"
            else:
                # Use the emotion model to modify the emotional state
                self.emotional_state = self.emotion_model.modify_state(
                    self.emotional_state,
                    request.modification_type,
                    request.value,
                    request.specific_emotion
                )
                
                # Update source and description after modification
                self.emotional_state.source = source
                
                if request.modification_type == "specific":
                    self.emotional_state.description = f"Modified {request.specific_emotion} due to: {reason}"
                else:
                    self.emotional_state.description = f"Modified emotional state due to: {reason}"
            
            # Update timestamp
            self.emotional_state.timestamp = utils.get_current_time()
            
            # Publish updated state
            self.state_publisher.publish(self.emotional_state)
            
        except ValueError as e:
            response.success = False
            response.error_message = str(e)
            # Revert to original state
            self.emotional_state = original_state
        
        # Set response
        response.updated_emotional_state = self.emotional_state
        
        return response

    def update_primary_emotion(self):
        """Update the primary_emotion field based on the current emotion model."""
        # Use the emotion model to determine the primary emotion
        primary_emotion = self.emotion_model.get_primary_emotion(self.emotional_state)
        
        # Only log if the primary emotion has changed
        if self.emotional_state.primary_emotion != primary_emotion:
            # Log the basic emotion values for debugging
            emotions = self.emotion_model.get_all_emotions()
            emotion_values = ", ".join([f"{e}: {self.emotion_model.get_emotion_value(self.emotional_state, e):.2f}" for e in emotions])
            self.get_logger().info(f"ALAINA: Emotion values - {emotion_values}")
            self.get_logger().info(f"ALAINA: Primary emotion updated to: {primary_emotion}")
        
        # Set the primary emotion
        self.emotional_state.primary_emotion = primary_emotion

def main(args=None):
    # Create the ROS log directory if it doesn't exist
    os.makedirs('/root/.ros/log', exist_ok=True)
    
    rclpy.init(args=args)
    node = EmotionalStateManager()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 