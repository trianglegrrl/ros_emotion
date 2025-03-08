#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import EmotionalState, SensoryInput, RuminationUpdate
import requests
import json
import uuid
import time
import ros_emotion.utils as utils

class LLMIntegration(Node):
    def __init__(self):
        super().__init__('llm_integration')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.llm_config = self.config.get('llm_integration', {})
        
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
        
        # Store the current emotional state
        self.current_emotional_state = None
        
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
        self.endpoint = self.llm_config.get('endpoint', 'http://localhost:8000/v1/chat/completions')
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
        """Store the current emotional state."""
        self.current_emotional_state = msg
        self.get_logger().debug(f"ALAINA: Updated emotional state: {msg.description}")
    
    def sensory_input_callback(self, msg):
        """Process incoming sensory input."""
        self.get_logger().info(f"ALAINA: Received sensory input for LLM processing: {msg.description}")
        
        # Add to recent inputs
        self.recent_inputs.append(msg)
        
        # Keep only the most recent inputs
        if len(self.recent_inputs) > self.max_recent_inputs:
            self.recent_inputs.pop(0)
    
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
        """Query the LLM with the current emotional state and sensory input."""
        # Format the emotional state for the prompt
        emotional_state_str = self.format_emotional_state(self.current_emotional_state)
        
        # Create the prompt
        prompt = f"""
Current Emotional State:
{emotional_state_str}

Sensory Input:
Type: {sensory_input.input_type}
Description: {sensory_input.description}
Intensity: {sensory_input.intensity}
Source: {sensory_input.source}

Based on this sensory input, how should the robot's emotional state change? 
Provide a response in the following JSON format:
{{
  "pleasure_change": <float between -1.0 and 1.0>,
  "arousal_change": <float between -1.0 and 1.0>,
  "dominance_change": <float between -1.0 and 1.0>,
  "happiness_change": <float between -1.0 and 1.0>,
  "sadness_change": <float between -1.0 and 1.0>,
  "anger_change": <float between -1.0 and 1.0>,
  "fear_change": <float between -1.0 and 1.0>,
  "disgust_change": <float between -1.0 and 1.0>,
  "surprise_change": <float between -1.0 and 1.0>,
  "description": "<brief description of the emotional response>"
}}
"""
        
        # Prepare the request
        headers = {
            'Content-Type': 'application/json'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': self.system_prompt
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': self.max_tokens,
            'temperature': self.temperature
        }
        
        # Make the request
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Extract the JSON part from the response
                try:
                    # Try to find JSON in the response
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        return json.loads(json_str)
                    else:
                        self.get_logger().warning(f"ALAINA: No JSON found in LLM response: {content}")
                        return {}
                except json.JSONDecodeError:
                    self.get_logger().warning(f"ALAINA: Failed to parse JSON from LLM response: {content}")
                    return {}
            else:
                self.get_logger().error(f"ALAINA: LLM request failed with status {response.status_code}: {response.text}")
                return {}
        except requests.exceptions.RequestException as e:
            self.get_logger().error(f"ALAINA: LLM request error: {str(e)}")
            return {}
    
    def format_emotional_state(self, state):
        """Format the emotional state for the LLM prompt."""
        return f"""
Dimensional Model:
- Pleasure: {state.pleasure:.2f} (-1.0 to 1.0)
- Arousal: {state.arousal:.2f} (-1.0 to 1.0)
- Dominance: {state.dominance:.2f} (-1.0 to 1.0)

Basic Emotions:
- Happiness: {state.happiness:.2f} (0.0 to 1.0)
- Sadness: {state.sadness:.2f} (0.0 to 1.0)
- Anger: {state.anger:.2f} (0.0 to 1.0)
- Fear: {state.fear:.2f} (0.0 to 1.0)
- Disgust: {state.disgust:.2f} (0.0 to 1.0)
- Surprise: {state.surprise:.2f} (0.0 to 1.0)

Overall Intensity: {state.intensity:.2f}
"""
    
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
        node.get_logger().info("ALAINA: Keyboard interrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 