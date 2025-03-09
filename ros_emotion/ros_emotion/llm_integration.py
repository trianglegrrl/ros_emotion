#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import EmotionalState, SensoryInput, RuminationUpdate, EmotionalResponse
from ros_emotion.srv import EmotionModify
import requests
import json
import uuid
import time
import ros_emotion.utils as utils
from ros_emotion.emotion_model import create_emotion_model

class LLMIntegration(Node):
    def __init__(self):
        super().__init__('llm_integration')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.llm_config = self.config.get('llm_integration', {})
        
        # Initialize the emotion model
        emotion_model_type = self.config.get('emotional_state_manager', {}).get('emotion_model_type', 'pad_basic')
        self.emotion_model = create_emotion_model(emotion_model_type)
        self.get_logger().info(f"ALAINA: Created emotion model of type {emotion_model_type}")
        
        # Create QoS profile
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create publishers
        self.rumination_pub = self.create_publisher(
            RuminationUpdate, 
            'rumination_update', 
            qos
        )
        
        self.emotional_response_pub = self.create_publisher(
            EmotionalResponse,
            'emotional_response',
            qos
        )
        
        # Create subscribers
        self.emotional_state_sub = self.create_subscription(
            EmotionalState,
            'emotional_state',
            self.emotional_state_callback,
            qos
        )
        
        self.sensory_input_sub = self.create_subscription(
            SensoryInput,
            'sensory_input',
            self.sensory_input_callback,
            qos
        )
        
        # Service client for modifying emotional state
        self.emotion_modify_client = self.create_client(
            EmotionModify,
            'modify_emotional_state'
        )
        
        # Store the current emotional state
        self.current_emotional_state = EmotionalState()
        
        # Store recent sensory inputs
        self.recent_inputs = []
        self.max_recent_inputs = 5
        
        # Create timer for processing inputs
        update_frequency = self.llm_config.get('update_frequency', 1.0)
        self.process_timer = self.create_timer(
            1.0 / update_frequency,
            self.process_inputs
        )
        
        # LLM configuration
        self.api_base_url = self.llm_config.get('api_base_url', 'http://localhost:8000/api')
        self.api_key = self.llm_config.get('api_key', '')
        self.model = self.llm_config.get('model', 'gpt-3.5-turbo')
        self.max_tokens = self.llm_config.get('max_tokens', 150)
        self.temperature = self.llm_config.get('temperature', 0.7)
        self.system_prompt = self.llm_config.get('system_prompt', 
            "You are an emotion processing system for a robot. Given the current emotional state and a sensory input, determine how the robot's emotional state should change."
        )
        self.timeout = self.llm_config.get('timeout', 5.0)
        
        self.get_logger().info("ALAINA: LLM Integration initialized")
    
    def emotional_state_callback(self, msg):
        """Store the latest emotional state."""
        self.current_emotional_state = msg
        
        # Ensure primary_emotion is set, even if missing in the message
        if not hasattr(self.current_emotional_state, 'primary_emotion') or not self.current_emotional_state.primary_emotion:
            # Use emotion model to determine primary emotion
            self.current_emotional_state.primary_emotion = self.emotion_model.get_primary_emotion(self.current_emotional_state)
            self.get_logger().info(f"ALAINA: Added missing primary_emotion: {self.current_emotional_state.primary_emotion}")
    
    def sensory_input_callback(self, msg):
        """Process sensory input using LLM"""
        self.get_logger().info(f"ALAINA: Received sensory input: {msg.description}")
        
        # Create an identifier for this sensory input
        input_id = str(uuid.uuid4())
        
        # Process with LLM to determine emotional impact
        response = self.query_llm_for_sensory_processing(msg, input_id)
        
        if response:
            # Update emotional state based on LLM response
            self.update_emotional_state(response, input_id, msg, is_rumination=False)
        else:
            self.get_logger().error("ALAINA: Failed to get LLM response for sensory input")
    
    def query_llm_for_sensory_processing(self, sensory_input, input_id):
        """Query LLM to analyze sensory input and determine emotional impact"""
        try:
            # If we have an existing emotional state, consider it when generating the response
            if self.current_emotional_state:
                pleasure = self.emotion_model.get_emotion_value(self.current_emotional_state, "pleasure")
                arousal = self.emotion_model.get_emotion_value(self.current_emotional_state, "arousal")
                self.get_logger().info(f"ALAINA: Current emotional state before processing - Pleasure: {pleasure:.2f}, Arousal: {arousal:.2f}")
                
                # Log primary emotion
                primary_emotion = self.emotion_model.get_primary_emotion(self.current_emotional_state)
                self.get_logger().info(f"ALAINA: Current primary emotion: {primary_emotion}")
            
            # Build prompt for the LLM
            prompt = self.build_sensory_processing_prompt(sensory_input)
            
            # Call LLM API
            response = self.call_llm_api(prompt)
            
            if response:
                self.get_logger().info(f"ALAINA: LLM response for input {input_id}: {response[:100]}...")
                
                # Parse the response
                parsed_response = self.parse_llm_response(response)
                return parsed_response
            else:
                return None
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error querying LLM for sensory processing: {str(e)}")
            # Add traceback for more detailed error information
            import traceback
            self.get_logger().error(f"ALAINA: Traceback: {traceback.format_exc()}")
            return None
    
    def build_sensory_processing_prompt(self, sensory_input):
        """Build a prompt for the LLM to process sensory input"""
        # Get dimensions and emotions from the emotion model
        dimensions = self.emotion_model.get_dimensions()
        emotions = self.emotion_model.get_all_emotions()
        
        # Format the current emotional state using the emotion model
        current_state = {}
        
        # Add dimensional values
        for dim in dimensions:
            current_state[dim] = self.emotion_model.get_emotion_value(self.current_emotional_state, dim)
        
        # Add basic emotion values
        for emotion in emotions:
            current_state[emotion] = self.emotion_model.get_emotion_value(self.current_emotional_state, emotion)
        
        # Add other state information
        current_state["intensity"] = self.emotion_model.calculate_intensity(self.current_emotional_state)
        current_state["description"] = self.current_emotional_state.description if hasattr(self.current_emotional_state, 'description') else ""
        
        # Get primary emotion from the emotion model
        primary_emotion = self.emotion_model.get_primary_emotion(self.current_emotional_state)
        self.get_logger().info(f"ALAINA: Current primary emotion: {primary_emotion}")
        
        # Add primary emotion to the state
        current_state["primary_emotion"] = primary_emotion
        
        # Build the prompt
        prompt = f"""You are the emotional processing system for a robot. 
Given the following sensory input and current emotional state, determine how the emotional state should change:

CURRENT EMOTIONAL STATE:
{json.dumps(current_state, indent=2)}

SENSORY INPUT:
Type: {sensory_input.input_type}
Description: {sensory_input.description}
Source: {sensory_input.source}
Intensity: {sensory_input.intensity}
Priority: {sensory_input.priority}

Based on this information, determine:
1. How should the emotional state change? 
2. What should be the primary emotion after this input?
3. What should be the response text that explains this change?

IMPORTANT: You MUST use one of these exact emotion names: {", ".join(emotions)}

Respond ONLY with a valid JSON object in the following format:
{{
  "pleasure_delta": float (-1.0 to 1.0),
  "arousal_delta": float (-1.0 to 1.0),
  "dominance_delta": float (-1.0 to 1.0),
  "primary_emotion": string (one of: {", ".join([f'"{e}"' for e in emotions])}),
  "intensity": float (0.0 to 1.0),
  "confidence": float (0.0 to 1.0),
  "response_text": string
}}"""
        
        return prompt
    
    def call_llm_api(self, prompt):
        """Call the LLM API with the given prompt"""
        try:
            # Create request payload
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            # For demonstration, we'll use a simple response
            # In a real implementation, this would make an API call to an LLM service
            
            self.get_logger().info("ALAINA: Simulating LLM API call (would connect to real API in production)")
            
            # Extract description if possible, or use default
            description = "input"
            try:
                desc_start = prompt.find("Description: ")
                if desc_start != -1:
                    desc_start += len("Description: ")
                    desc_end = prompt.find("\n", desc_start)
                    if desc_end != -1:
                        description = prompt[desc_start:desc_end]
                    else:
                        description = prompt[desc_start:]
            except:
                pass
            
            # Mock response for demonstration
            return json.dumps({
                "pleasure_delta": 0.2 if "friendly" in prompt or "happy" in prompt else -0.2,
                "arousal_delta": 0.3 if "exciting" in prompt or "surprising" in prompt else -0.1,
                "dominance_delta": 0.1 if "control" in prompt or "mastery" in prompt else -0.1,
                "primary_emotion": "happiness" if "friendly" in prompt or "happy" in prompt else "sadness",
                "intensity": 0.7,
                "confidence": 0.8,
                "response_text": f"Processing sensory input: {description}"
            })
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error calling LLM API: {str(e)}")
            return None
    
    def parse_llm_response(self, response_text):
        """Parse the LLM response"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            self.get_logger().error(f"ALAINA: Error parsing LLM response: {str(e)}")
            return None
    
    def update_emotional_state(self, llm_response, input_id, original_input=None, is_rumination=False):
        """Update the emotional state based on LLM response"""
        if not llm_response:
            return
        
        # Create the emotional response message
        response_msg = EmotionalResponse()
        response_msg.timestamp.sec = int(time.time())
        response_msg.timestamp.nanosec = int((time.time() % 1) * 1e9)
        response_msg.stimulus_id = input_id
        response_msg.is_rumination = is_rumination
        response_msg.response_text = llm_response.get("response_text", "")
        response_msg.source = "llm"
        response_msg.previous_state = self.current_emotional_state
        response_msg.pleasure_delta = llm_response.get("pleasure_delta", 0.0)
        response_msg.arousal_delta = llm_response.get("arousal_delta", 0.0)
        response_msg.dominance_delta = llm_response.get("dominance_delta", 0.0)
        response_msg.primary_emotion = llm_response.get("primary_emotion", "neutral")
        response_msg.intensity = llm_response.get("intensity", 0.5)
        response_msg.confidence = llm_response.get("confidence", 0.5)
        response_msg.metadata = json.dumps({
            "original_input": original_input.description if original_input else "none"
        })
        
        # Publish the emotional response
        self.emotional_response_pub.publish(response_msg)
        self.get_logger().info(f"ALAINA: Published emotional response for {input_id}")
        
        # Wait for service to be available
        while not self.emotion_modify_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ALAINA: Waiting for emotion_modify service...')
        
        # Create service request for pleasure
        pleasure_request = EmotionModify.Request()
        pleasure_request.modification_type = "relative"
        pleasure_request.specific_emotion = "pleasure"
        pleasure_request.value = llm_response.get("pleasure_delta", 0.0)
        pleasure_request.reason = f"Sensory input: {original_input.description if original_input else 'rumination'}"
        pleasure_request.override_safety = False
        
        # Call service for pleasure
        pleasure_future = self.emotion_modify_client.call_async(pleasure_request)
        
        # Create service request for arousal
        arousal_request = EmotionModify.Request()
        arousal_request.modification_type = "relative"
        arousal_request.specific_emotion = "arousal"
        arousal_request.value = llm_response.get("arousal_delta", 0.0)
        arousal_request.reason = f"Sensory input: {original_input.description if original_input else 'rumination'}"
        arousal_request.override_safety = False
        
        # Call service for arousal
        arousal_future = self.emotion_modify_client.call_async(arousal_request)
        
        # Create service request for dominance
        dominance_request = EmotionModify.Request()
        dominance_request.modification_type = "relative"
        dominance_request.specific_emotion = "dominance"
        dominance_request.value = llm_response.get("dominance_delta", 0.0)
        dominance_request.reason = f"Sensory input: {original_input.description if original_input else 'rumination'}"
        dominance_request.override_safety = False
        
        # Call service for dominance
        dominance_future = self.emotion_modify_client.call_async(dominance_request)
        
        # Create service request for primary emotion
        emotion_request = EmotionModify.Request()
        emotion_request.modification_type = "specific"
        emotion_request.specific_emotion = llm_response.get("primary_emotion", "neutral")
        emotion_request.value = llm_response.get("intensity", 0.5)
        emotion_request.reason = f"Sensory input: {original_input.description if original_input else 'rumination'}"
        emotion_request.override_safety = False
        
        # Call service for primary emotion
        emotion_future = self.emotion_modify_client.call_async(emotion_request)
        
        # Add callbacks
        pleasure_future.add_done_callback(lambda f: self.emotion_modify_callback(f, input_id, "pleasure"))
        arousal_future.add_done_callback(lambda f: self.emotion_modify_callback(f, input_id, "arousal"))
        dominance_future.add_done_callback(lambda f: self.emotion_modify_callback(f, input_id, "dominance"))
        emotion_future.add_done_callback(lambda f: self.emotion_modify_callback(f, input_id, "primary_emotion"))
    
    def emotion_modify_callback(self, future, input_id, emotion_type):
        """Callback for emotion modify service response"""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f"ALAINA: Emotional state ({emotion_type}) updated successfully for {input_id}")
            else:
                self.get_logger().error(f"ALAINA: Failed to update emotional state ({emotion_type}) for {input_id}: {response.error_message}")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Service call failed: {str(e)}")
    
    def process_inputs(self):
        """Process pending sensory inputs with the LLM."""
        if not self.recent_inputs or not self.current_emotional_state:
            return
        
        # Get the most recent input
        sensory_input = self.recent_inputs.pop()
        
        # Process with LLM
        try:
            response = self.query_llm(sensory_input)
            self.get_logger().info(f"ALAINA: LLM response: {response}")
            
            # Parse the response and generate a rumination update
            self.generate_rumination_update(sensory_input, response)
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error processing input with LLM: {str(e)}")
    
    def query_llm(self, sensory_input):
        """Query the LLM directly (not through the service) for rapid prototyping."""
        pass
    
    def format_emotional_state(self, state):
        """Format the emotional state for the LLM prompt."""
        return self.emotion_model.format_emotional_state(state)
    
    def generate_rumination_update(self, sensory_input, llm_response):
        """Generate a rumination update from the LLM response."""
        # Create a new rumination update message
        msg = RuminationUpdate()
        
        # Set timestamp
        msg.timestamp = utils.get_current_time()
        
        # Set original input ID (using source and timestamp as a unique identifier)
        input_timestamp = sensory_input.timestamp.sec + sensory_input.timestamp.nanosec / 1e9
        msg.original_input_id = f"{sensory_input.source}_{input_timestamp}"
        
        # Set rumination stage (initial stage)
        msg.rumination_stage = 0
        
        # Set elapsed time (just started)
        msg.elapsed_time = utils.create_duration(0.0)
        
        # Set intensity (based on sensory input intensity)
        msg.intensity = sensory_input.intensity
        
        # Set changes from LLM response
        msg.pleasure_change = llm_response.get('pleasure_change', 0.0)
        msg.arousal_change = llm_response.get('arousal_change', 0.0)
        msg.dominance_change = llm_response.get('dominance_change', 0.0)
        msg.happiness_change = llm_response.get('happiness_change', 0.0)
        msg.sadness_change = llm_response.get('sadness_change', 0.0)
        msg.anger_change = llm_response.get('anger_change', 0.0)
        msg.fear_change = llm_response.get('fear_change', 0.0)
        msg.disgust_change = llm_response.get('disgust_change', 0.0)
        msg.surprise_change = llm_response.get('surprise_change', 0.0)
        
        # Set description
        msg.description = llm_response.get('description', f"Emotional response to {sensory_input.description}")
        
        # This is the initial update, not final
        msg.is_final = False
        
        # Publish the rumination update
        self.rumination_pub.publish(msg)
        
        self.get_logger().info(f"ALAINA: Published initial rumination update for: {sensory_input.description}")


def main(args=None):
    rclpy.init(args=args)
    node = LLMIntegration()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 