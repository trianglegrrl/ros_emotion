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
from ros_emotion.personality_model import create_personality_model
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import os

class LLMIntegration(Node):
    def __init__(self):
        super().__init__('llm_integration')
        
        # Load configuration
        self.config = utils.load_config(self, 'emotion_config.yaml').get('llm_integration', {})
        
        # LLM API configuration
        self.api_key = os.environ.get('LLM_API_KEY', 'demo-key')
        self.api_url = self.config.get('api_url', 'http://localhost:8000/api/chat')
        self.model = self.config.get('model', 'gpt-3.5-turbo')
        self.max_tokens = self.config.get('max_tokens', 1024)
        self.temperature = self.config.get('temperature', 0.7)
        
        # Storage for inputs and state
        self.input_queue = []
        self.processed_ids = set()
        self.current_emotional_state = None
        self.processing_lock = False
        
        # Initialize the emotion model
        emotion_model_type = self.config.get('emotion_model_type', 'pad_basic')
        self.emotion_model = create_emotion_model(emotion_model_type)
        
        # Initialize the personality model
        personality_model_type = self.config.get('personality_model_type', 'hybrid')
        personality_config = self.config.get('personality', {})
        self.personality_model = create_personality_model(personality_model_type, personality_config)
        
        # Use a callback group that allows concurrent callbacks
        callback_group = ReentrantCallbackGroup()
        
        # Define QoS profile for reliable communication
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribe to emotional state updates
        self.state_sub = self.create_subscription(
            EmotionalState,
            'emotional_state',
            self.emotional_state_callback,
            10,
            callback_group=callback_group
        )
        
        # Subscribe to sensory input
        self.sensory_input_sub = self.create_subscription(
            SensoryInput,
            'sensory_input',
            self.sensory_input_callback,
            qos,
            callback_group=callback_group
        )
        
        # Publisher for emotional responses
        self.response_publisher = self.create_publisher(
            EmotionalResponse,
            'emotional_response',
            10
        )
        
        # Create a client for the emotion modify service
        self.emotion_modify_client = self.create_client(
            EmotionModify,
            'modify_emotional_state',
            callback_group=callback_group
        )
        
        # Create timer for processing inputs
        process_frequency = self.config.get('process_frequency', 1.0)
        self.process_timer = self.create_timer(
            1.0 / process_frequency,
            self.process_inputs,
            callback_group=callback_group
        )
        
        self.get_logger().info("ALAINA: LLM Integration initialized")
        self.get_logger().info(f"ALAINA: Using personality model: {personality_model_type}")
        self.get_logger().debug(f"ALAINA: Personality traits: {self.personality_model.format_personality_traits()}")
    
    def emotional_state_callback(self, msg):
        """Store the current emotional state"""
        self.current_emotional_state = msg
        self.get_logger().debug(f"ALAINA: Updated emotional state, primary emotion: {msg.primary_emotion}")
    
    def sensory_input_callback(self, msg):
        """Process incoming sensory input"""
        if not self.current_emotional_state:
            self.get_logger().warn("ALAINA: Received sensory input but emotional state is not initialized yet")
            return
            
        # Generate a unique ID for this input
        input_id = str(uuid.uuid4())
        
        # Add to processing queue
        self.input_queue.append((msg, input_id))
        
        self.get_logger().info(f"ALAINA: Queued sensory input [{input_id}]: {msg.description}")
    
    def query_llm_for_sensory_processing(self, sensory_input, input_id):
        """Query the LLM to process a sensory input"""
        try:
            # Build the prompt
            prompt = self.build_sensory_processing_prompt(sensory_input)
            
            # Call the LLM API
            self.get_logger().info(f"ALAINA: Calling LLM for sensory input [{input_id}]")
            response_text = self.call_llm_api(prompt)
            
            if not response_text:
                self.get_logger().error(f"ALAINA: Empty response from LLM for sensory input [{input_id}]")
                return None
                
            # Parse the response
            llm_data = self.parse_llm_response(response_text)
            
            if not llm_data:
                self.get_logger().error(f"ALAINA: Failed to parse LLM response for sensory input [{input_id}]")
                return None
                
            # Process the LLM response
            self.update_emotional_state(llm_data, input_id, sensory_input)
            
            return llm_data
            
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
        
        # Get personality context
        personality_context = self.personality_model.get_llm_context()
        personality_traits = self.personality_model.get_all_traits()
        
        # Add personality traits to the state
        current_state["personality"] = {
            "traits": {k: v for k, v in personality_traits.items() if k in 
                      ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']},
            "description": personality_context
        }
        
        # Build the prompt
        prompt = f"""You are the emotional processing system for a robot with a specific personality. 
Given the following sensory input, current emotional state, and personality profile, determine how the emotional state should change:

PERSONALITY PROFILE:
{personality_context}

CURRENT EMOTIONAL STATE:
{json.dumps(current_state, indent=2)}

SENSORY INPUT:
Type: {sensory_input.input_type}
Description: {sensory_input.description}
Source: {sensory_input.source}
Intensity: {sensory_input.intensity}
Priority: {sensory_input.priority}

Based on this information, and considering the personality traits (especially {max(personality_traits.items(), key=lambda x: abs(x[1] - 0.5))[0]}), determine:
1. How should the emotional state change? 
2. What should be the primary emotion after this input?
3. What should be the response text that explains this change?

IMPORTANT: 
- The personality will affect how strongly and in what way the robot responds to the input
- You MUST use one of these exact emotion names: {", ".join(emotions)}
- Consider that high neuroticism means more emotional reactivity
- High extraversion means more positive response to social stimuli
- High agreeableness means less anger responses
- High openness means more curious responses
- High conscientiousness means more controlled responses

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
            
            # Add API key to headers if not using localhost
            headers = {}
            if not self.api_url.startswith('http://localhost'):
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Set longer timeout for API call
            timeout = 30.0  # 30 seconds
            
            # Call the API
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            # Check response status
            if response.status_code != 200:
                self.get_logger().error(f"ALAINA: API request failed with status code {response.status_code}: {response.text}")
                return None
                
            # Parse response JSON
            response_json = response.json()
            
            # Extract content from response (adapt this based on your API's response format)
            if isinstance(response_json, dict):
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    # OpenAI-like API format
                    return response_json["choices"][0]["message"]["content"]
                elif "response" in response_json:
                    # Custom API format
                    return response_json["response"]
                else:
                    # Try to find any text content in the response
                    for key, value in response_json.items():
                        if isinstance(value, str) and len(value) > 10:
                            return value
            
            # Fallback: return the whole response as string
            return str(response_json)
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error calling LLM API: {str(e)}")
            return None
    
    def parse_llm_response(self, response_text):
        """Parse the LLM response to extract structured data"""
        try:
            # Look for a JSON object in the response
            import re
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(1)
                return json.loads(json_text)
            else:
                self.get_logger().error(f"ALAINA: Could not find JSON in LLM response: {response_text}")
                return None
                
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error parsing LLM response: {str(e)}")
            return None
    
    def update_emotional_state(self, llm_response, input_id, original_input=None, is_rumination=False):
        """Update the emotional state based on LLM response"""
        try:
            # Create a new emotional response message
            response = EmotionalResponse()
            
            # Set timestamp
            response.timestamp = utils.get_current_time()
            
            # Set stimulus ID
            response.stimulus_id = input_id
            
            # Set rumination flag
            response.is_rumination = is_rumination
            
            # Set response text
            response.response_text = llm_response.get("response_text", "")
            
            # Set source
            response.source = "llm"
            
            # Set previous state (current state before update)
            response.previous_state = utils.copy_emotional_state(self.current_emotional_state)
            
            # Copy deltas from LLM response
            response.pleasure_delta = llm_response.get("pleasure_delta", 0.0)
            response.arousal_delta = llm_response.get("arousal_delta", 0.0)
            response.dominance_delta = llm_response.get("dominance_delta", 0.0)
            
            # Set primary emotion
            response.primary_emotion = llm_response.get("primary_emotion", "")
            
            # Set intensity and confidence
            response.intensity = llm_response.get("intensity", 0.0)
            response.confidence = llm_response.get("confidence", 0.0)
            
            # Create metadata
            metadata = {
                "input_type": original_input.input_type if original_input else "unknown",
                "processing_time": time.time(),
                "model": self.model,
                "personality_influence": {
                    "primary_trait": max(self.personality_model.get_all_traits().items(), key=lambda x: abs(x[1] - 0.5))[0]
                }
            }
            response.metadata = json.dumps(metadata)
            
            # Let the personality model modulate the response based on traits
            modulated_response = self.personality_model.modulate_emotional_response(
                self.current_emotional_state, 
                response
            )
            
            # Publish the emotional response
            self.response_publisher.publish(modulated_response)
            
            # Update emotional state using service
            self.update_emotional_dimensions(
                modulated_response.pleasure_delta, 
                modulated_response.arousal_delta, 
                modulated_response.dominance_delta,
                input_id
            )
            
            # Return the modulated response
            return modulated_response
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error updating emotional state: {str(e)}")
            return None
    
    def update_emotional_dimensions(self, pleasure_delta, arousal_delta, dominance_delta, input_id):
        """Update emotional dimensions using the emotion_modify service"""
        
        # Wait for service to be available
        if not self.emotion_modify_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("ALAINA: Emotion modify service not available")
            return False
        
        try:
            # Create request for pleasure
            if pleasure_delta != 0.0:
                pleasure_request = EmotionModify.Request()
                pleasure_request.modification_type = "relative"
                pleasure_request.specific_emotion = "pleasure"
                pleasure_request.value = pleasure_delta
                pleasure_request.reason = f"LLM response to input {input_id}"
                pleasure_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(pleasure_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, input_id, "pleasure")
                )
            
            # Create request for arousal
            if arousal_delta != 0.0:
                arousal_request = EmotionModify.Request()
                arousal_request.modification_type = "relative"
                arousal_request.specific_emotion = "arousal"
                arousal_request.value = arousal_delta
                arousal_request.reason = f"LLM response to input {input_id}"
                arousal_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(arousal_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, input_id, "arousal")
                )
            
            # Create request for dominance
            if dominance_delta != 0.0:
                dominance_request = EmotionModify.Request()
                dominance_request.modification_type = "relative"
                dominance_request.specific_emotion = "dominance"
                dominance_request.value = dominance_delta
                dominance_request.reason = f"LLM response to input {input_id}"
                dominance_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(dominance_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, input_id, "dominance")
                )
            
            return True
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error updating emotional dimensions: {str(e)}")
            return False
    
    def emotion_modify_callback(self, future, input_id, emotion_type):
        """Callback for emotion modify service"""
        try:
            response = future.result()
            if response.success:
                self.get_logger().debug(f"ALAINA: Successfully updated {emotion_type} for input {input_id}")
            else:
                self.get_logger().warn(f"ALAINA: Failed to update {emotion_type} for input {input_id}: {response.error_message}")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error in emotion modify callback: {str(e)}")
    
    def process_inputs(self):
        """Process queued inputs"""
        if self.processing_lock or not self.current_emotional_state or not self.input_queue:
            return
            
        self.processing_lock = True
        
        try:
            # Get next input
            sensory_input, input_id = self.input_queue.pop(0)
            
            # Process the input
            self.query_llm_for_sensory_processing(sensory_input, input_id)
            
            # Add to processed set
            self.processed_ids.add(input_id)
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error processing inputs: {str(e)}")
        
        finally:
            self.processing_lock = False
    
    def query_llm(self, sensory_input):
        """Alias for query_llm_for_sensory_processing"""
        return self.query_llm_for_sensory_processing(sensory_input, str(uuid.uuid4()))
    
    def format_emotional_state(self, state):
        """Format an emotional state for logging or display"""
        return self.emotion_model.format_emotional_state(state)
    
    def generate_rumination_update(self, sensory_input, llm_response):
        """Generate a rumination update from an LLM response to sensory input"""
        # In a real implementation, this would process the response
        # and create a RuminationUpdate message to be published.
        # For now, this is a stub.
        pass

def main(args=None):
    rclpy.init(args=args)
    
    node = LLMIntegration()
    
    # Use a MultiThreadedExecutor to enable processing concurrent callbacks
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info("ALAINA: Shutting down LLM Integration node")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 