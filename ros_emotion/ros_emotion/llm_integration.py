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
            'emotion_modify'
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
        """Store the current emotional state."""
        self.current_emotional_state = msg
        self.get_logger().debug(f"ALAINA: Updated emotional state: {msg.description}")
    
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
            return None
    
    def build_sensory_processing_prompt(self, sensory_input):
        """Build a prompt for the LLM to process sensory input"""
        # Format the current emotional state
        current_state = {
            "pleasure": self.current_emotional_state.pleasure,
            "arousal": self.current_emotional_state.arousal,
            "dominance": self.current_emotional_state.dominance,
            "primary_emotion": self.current_emotional_state.primary_emotion,
            "secondary_emotion": self.current_emotional_state.secondary_emotion,
            "intensity": self.current_emotional_state.intensity
        }
        
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

Respond ONLY with a valid JSON object in the following format:
{
  "pleasure_delta": float (-1.0 to 1.0),
  "arousal_delta": float (-1.0 to 1.0),
  "dominance_delta": float (-1.0 to 1.0),
  "primary_emotion": string,
  "intensity": float (0.0 to 1.0),
  "confidence": float (0.0 to 1.0),
  "response_text": string
}"""
        
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
            
            # Simulate API response (for demo purposes)
            # In production, this would be: response = requests.post(f"{self.api_base_url}/completions", json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
            
            # Mock response for demonstration
            return json.dumps({
                "pleasure_delta": 0.2 if "friendly" in prompt or "happy" in prompt else -0.2,
                "arousal_delta": 0.3 if "exciting" in prompt or "surprising" in prompt else -0.1,
                "dominance_delta": 0.1 if "control" in prompt or "mastery" in prompt else -0.1,
                "primary_emotion": "joy" if "friendly" in prompt or "happy" in prompt else "sadness",
                "intensity": 0.7,
                "confidence": 0.8,
                "response_text": f"Processing sensory input: {prompt.split('Description: ')[1].split('\n')[0]}"
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
        
        # Create service request
        request = EmotionModify.Request()
        request.pleasure_delta = llm_response.get("pleasure_delta", 0.0)
        request.arousal_delta = llm_response.get("arousal_delta", 0.0)
        request.dominance_delta = llm_response.get("dominance_delta", 0.0)
        request.primary_emotion = llm_response.get("primary_emotion", "neutral")
        request.intensity = llm_response.get("intensity", 0.5)
        
        # Call service
        future = self.emotion_modify_client.call_async(request)
        future.add_done_callback(lambda f: self.emotion_modify_callback(f, input_id))
    
    def emotion_modify_callback(self, future, input_id):
        """Callback for emotion modify service response"""
        try:
            response = future.result()
            self.get_logger().info(f"ALAINA: Emotional state updated successfully for {input_id}")
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
                self.api_base_url + '/completions',
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