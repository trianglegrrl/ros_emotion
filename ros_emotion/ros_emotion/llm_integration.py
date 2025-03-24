#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

# Fix import of custom messages
try:
    from ros_emotion_msgs.msg import EmotionalState, SensoryInput, RuminationUpdate, EmotionalResponse
    from ros_emotion_msgs.srv import EmotionModify
except ImportError:
    # Fallback to local message definition
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
import logging
from dotenv import load_dotenv
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rcl_interfaces.msg import ParameterDescriptor, ParameterType
from std_msgs.msg import String, Float32, Float32MultiArray, Bool, Header

class LLMIntegration(Node):
    def __init__(self):
        super().__init__('llm_integration')
        
        # Load environment variables (if not already loaded)
        load_dotenv()
        
        # Create LLM client
        self.llm_client = LLMClient(node=self)
        
        # Load configuration
        self.config = utils.load_config(self)
        self.llm_config = self.config.get('llm_integration', {})
        
        # Create QoS profile
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Initialize emotional state
        self.emotional_state = {
            'pleasure': 0.0, 
            'arousal': 0.0, 
            'dominance': 0.0,
            'primary_emotion': 'neutral',
            'secondary_emotion': 'neutral',
            'emotion_intensities': {}
        }
        
        # Set up processing queue
        self.input_queue = deque()
        self.is_processing = False
        self.processing_executor = ThreadPoolExecutor(max_workers=1)
        
        # Create callback groups
        self.timer_callback_group = MutuallyExclusiveCallbackGroup()
        self.subscription_callback_group = MutuallyExclusiveCallbackGroup()
        
        # Create timer for processing inputs
        self.processing_timer = self.create_timer(
            0.1,  # 10 Hz
            self.process_inputs,
            callback_group=self.timer_callback_group
        )
        
        # Create publishers
        self.emotional_state_pub = self.create_publisher(
            EmotionalState, 
            'emotional_state', 
            qos
        )
        
        self.emotion_vector_pub = self.create_publisher(
            Float32MultiArray, 
            'emotion', 
            qos
        )
        
        # Create subscribers
        self.sensory_input_sub = self.create_subscription(
            SensoryInput,
            'sensory_input',
            self.sensory_input_callback,
            qos,
            callback_group=self.subscription_callback_group
        )
        
        self.emotional_state_sub = self.create_subscription(
            EmotionalState,
            'emotional_state',
            self.emotional_state_callback,
            qos,
            callback_group=self.subscription_callback_group
        )
        
        # Log initialization
        self.get_logger().info('ALAINA: LLM integration node initialized')
        self.get_logger().info(f'ALAINA: Using LLM model: {self.llm_client.get_model_name()}')
        self.get_logger().info(f'ALAINA: Using API host: {self.llm_client.api_host}')

    def emotional_state_callback(self, msg):
        """Update the internal emotional state from the message"""
        self.emotional_state = {
            'pleasure': msg.pleasure,
            'arousal': msg.arousal,
            'dominance': msg.dominance,
            'primary_emotion': msg.primary_emotion,
            'secondary_emotion': msg.secondary_emotion
        }

    def sensory_input_callback(self, msg):
        """Handle incoming sensory input messages"""
        self.get_logger().debug(f'ALAINA: Received sensory input: {msg.input_type}')
        # Add the input to the queue for processing
        self.input_queue.append(msg)
        
        if len(self.input_queue) > 0:
            self.get_logger().debug(f'ALAINA: Queue size: {len(self.input_queue)}')

    def query_llm_for_sensory_processing(self, sensory_input, input_id):
        """Query the LLM for processing the sensory input"""
        try:
            # Build the prompt based on the sensory input
            prompt = self.build_sensory_processing_prompt(sensory_input)
            
            # Query the LLM
            messages = [{"role": "user", "content": prompt}]
            
            # Get the LLM configuration
            temperature = self.llm_config.get('temperature', 0.7)
            system_prompt = self.llm_config.get('system_prompt', 
                "You are a cognitive-emotional processor module in a robot. " +
                "You analyze sensory inputs and determine how they affect emotional state.")
            
            # Call the LLM API
            self.get_logger().info(f'ALAINA: Querying LLM for input ID: {input_id}')
            response_text, full_response = self.llm_client.call_chat_completion(
                messages=messages, 
                temperature=temperature,
                system_prompt=system_prompt
            )
            
            # Parse LLM response and update emotional state
            if response_text:
                self.get_logger().debug(f'ALAINA: LLM response: {response_text[:100]}...')
                parsed_response = self.parse_llm_response(response_text)
                self.update_emotional_state(parsed_response, input_id, sensory_input)
            else:
                self.get_logger().error(f'ALAINA: Empty response from LLM for input {input_id}')
                
        except Exception as e:
            self.get_logger().error(f'ALAINA: Error querying LLM: {str(e)}')

    def build_sensory_processing_prompt(self, sensory_input):
        """Build the prompt for the LLM based on the sensory input and current emotional state"""
        # Convert sensory input to string representation
        input_type = sensory_input.input_type
        description = sensory_input.description
        metadata = json.loads(sensory_input.metadata) if sensory_input.metadata else {}
        
        # Format current emotional state
        formatted_state = self.format_emotional_state(self.emotional_state)
        
        # Build the prompt
        prompt = f"""
        ## SENSORY INPUT
        Type: {input_type}
        Description: {description}
        Intensity: {sensory_input.intensity}
        Confidence: {sensory_input.confidence}
        
        ## CURRENT EMOTIONAL STATE
        {formatted_state}
        
        ## TASK
        Analyze the above sensory input in the context of the current emotional state.
        Determine how this input should affect the emotional state of the system.
        
        For your response, provide:
        1. A brief analysis of the sensory input (2-3 sentences)
        2. The emotional response to this input
        3. Specific changes to the emotional state with numerical values
        
        Your response MUST follow this JSON format:
        ```json
        {{
            "analysis": "Your brief analysis of the sensory input",
            "emotional_response": "Description of the emotional response",
            "changes": {{
                "pleasure_delta": 0.0,  # Range: -1.0 to 1.0
                "arousal_delta": 0.0,   # Range: -1.0 to 1.0
                "dominance_delta": 0.0, # Range: -1.0 to 1.0
                "primary_emotion": "emotion_name", 
                "intensity": 0.0 # Range: 0.0 to 1.0
            }}
        }}
        ```
        
        Note: 
        - pleasure_delta: How pleasant/unpleasant is this input (-1.0 = very unpleasant, 1.0 = very pleasant)
        - arousal_delta: How activating/calming is this input (-1.0 = very calming, 1.0 = very activating)
        - dominance_delta: How much control the system feels (-1.0 = loss of control, 1.0 = gaining control)
        - Keep your deltas small for subtle changes (-0.3 to 0.3) and larger for significant changes
        """
        
        return prompt

    def call_llm_api(self, prompt):
        """
        Legacy method to maintain compatibility - routes to LLMClient
        """
        self.get_logger().warn('ALAINA: Using deprecated call_llm_api method, please update to use LLMClient')
        
        messages = [{"role": "user", "content": prompt}]
        response_text, _ = self.llm_client.call_chat_completion(messages=messages)
        return response_text

    def parse_llm_response(self, response_text):
        """Parse the response from the LLM"""
        try:
            # Extract JSON from the response if it's wrapped in backticks
            if '```json' in response_text:
                json_content = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_content = response_text.split('```')[1].strip()
            else:
                json_content = response_text.strip()
            
            # Parse the JSON response
            parsed = json.loads(json_content)
            return parsed
            
        except Exception as e:
            self.get_logger().error(f'ALAINA: Error parsing LLM response: {str(e)}')
            self.get_logger().error(f'ALAINA: Response: {response_text}')
            return None

    def update_emotional_state(self, llm_response, input_id, original_input=None, is_rumination=False):
        """Update the emotional state based on the LLM response"""
        if not llm_response:
            self.get_logger().warn('ALAINA: Empty LLM response, not updating emotional state')
            return
        
        try:
            # Extract changes from the response
            changes = llm_response.get('changes', {})
            
            # Get the deltas
            pleasure_delta = float(changes.get('pleasure_delta', 0.0))
            arousal_delta = float(changes.get('arousal_delta', 0.0))
            dominance_delta = float(changes.get('dominance_delta', 0.0))
            
            # Apply the deltas to the emotional state
            self.update_emotional_dimensions(
                pleasure_delta, 
                arousal_delta, 
                dominance_delta,
                input_id
            )
            
            # Get the new primary emotion
            primary_emotion = changes.get('primary_emotion', self.emotional_state.get('primary_emotion', 'neutral'))
            intensity = float(changes.get('intensity', 0.5))
            
            # Prepare the emotional state message
            msg = EmotionalState()
            msg.header = Header()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = f"emotion_update_{input_id}"
            
            msg.pleasure = self.emotional_state['pleasure']
            msg.arousal = self.emotional_state['arousal']
            msg.dominance = self.emotional_state['dominance']
            msg.primary_emotion = primary_emotion
            msg.secondary_emotion = self.emotional_state.get('secondary_emotion', 'neutral')
            msg.input_id = input_id
            msg.source = "llm_integration"
            
            # If we have original input, include its metadata
            if original_input:
                msg.trigger_type = original_input.input_type
                msg.trigger_description = original_input.description
            
            # Basic analysis
            if 'analysis' in llm_response:
                msg.analysis = llm_response['analysis']
            
            if 'emotional_response' in llm_response:
                msg.response = llm_response['emotional_response']
            
            # Publish the updated emotional state
            self.emotional_state_pub.publish(msg)
            
            # Update internal state
            self.emotional_state['pleasure'] = msg.pleasure
            self.emotional_state['arousal'] = msg.arousal
            self.emotional_state['dominance'] = msg.dominance
            self.emotional_state['primary_emotion'] = primary_emotion
            
            # Also publish as a vector for visualization
            self.publish_emotion_vector()
            
            # Log the update
            self.get_logger().info(f'ALAINA: Updated emotional state: P={msg.pleasure:.2f}, A={msg.arousal:.2f}, D={msg.dominance:.2f}, E={primary_emotion}')
            
            # If enabled, also generate a rumination update
            rumination_enabled = self.llm_config.get('enable_rumination', False)
            if rumination_enabled and not is_rumination and original_input:
                self.get_logger().info(f'ALAINA: Generating rumination for input {input_id}')
                self.processing_executor.submit(
                    self.generate_rumination_update, 
                    original_input, 
                    llm_response
                )
            
        except Exception as e:
            self.get_logger().error(f'ALAINA: Error updating emotional state: {str(e)}')

    def update_emotional_dimensions(self, pleasure_delta, arousal_delta, dominance_delta, input_id):
        """Update the emotional dimensions (PAD model) based on deltas"""
        # Get current values
        current_pleasure = self.emotional_state.get('pleasure', 0.0)
        current_arousal = self.emotional_state.get('arousal', 0.0)
        current_dominance = self.emotional_state.get('dominance', 0.0)
        
        # Calculate new values
        new_pleasure = current_pleasure + pleasure_delta
        new_arousal = current_arousal + arousal_delta
        new_dominance = current_dominance + dominance_delta
        
        # Clamp values to [-1, 1] range
        new_pleasure = max(-1.0, min(1.0, new_pleasure))
        new_arousal = max(-1.0, min(1.0, new_arousal))
        new_dominance = max(-1.0, min(1.0, new_dominance))
        
        # Apply decay if the changes are very small
        decay_threshold = self.llm_config.get('decay_threshold', 0.02)
        decay_factor = self.llm_config.get('decay_factor', 0.95)
        
        # If all deltas are smaller than the threshold, apply decay
        if (abs(pleasure_delta) < decay_threshold and 
            abs(arousal_delta) < decay_threshold and 
            abs(dominance_delta) < decay_threshold):
            
            new_pleasure = current_pleasure * decay_factor
            new_arousal = current_arousal * decay_factor
            new_dominance = current_dominance * decay_factor
            
            self.get_logger().debug(f'ALAINA: Applied emotional decay: {decay_factor}')
        
        # Update the state
        self.emotional_state['pleasure'] = new_pleasure
        self.emotional_state['arousal'] = new_arousal
        self.emotional_state['dominance'] = new_dominance
        
        self.get_logger().debug(f'ALAINA: Emotional deltas - P: {pleasure_delta:.2f}, A: {arousal_delta:.2f}, D: {dominance_delta:.2f}')
        self.get_logger().debug(f'ALAINA: New emotional state - P: {new_pleasure:.2f}, A: {new_arousal:.2f}, D: {new_dominance:.2f}')
        
        # Publish the updated dimensions
        self.publish_emotion_vector()

    def emotion_modify_callback(self, future, input_id, emotion_type):
        """Callback for when an emotion modification is complete"""
        try:
            result = future.result()
            if result:
                self.get_logger().info(f'ALAINA: Completed {emotion_type} for input {input_id}')
            else:
                self.get_logger().warn(f'ALAINA: Failed to complete {emotion_type} for input {input_id}')
        except Exception as e:
            self.get_logger().error(f'ALAINA: Error in {emotion_type} callback: {str(e)}')

    def process_inputs(self):
        """Process inputs from the queue"""
        if not self.input_queue or self.is_processing:
            return
        
        self.is_processing = True
        try:
            # Get the next input
            sensory_input = self.input_queue.popleft()
            
            # Process the input in a separate thread
            input_id = sensory_input.input_id
            future = self.processing_executor.submit(
                self.query_llm_for_sensory_processing, 
                sensory_input,
                input_id
            )
            future.add_done_callback(
                lambda f: self.emotion_modify_callback(f, input_id, "sensory processing")
            )
        finally:
            self.is_processing = False

    def query_llm(self, sensory_input):
        """Convenience method to query the LLM directly"""
        input_id = str(uuid.uuid4())
        return self.query_llm_for_sensory_processing(sensory_input, input_id)

    def format_emotional_state(self, state):
        """Format the emotional state as a string for prompts"""
        return f"Pleasure: {state['pleasure']:.2f}, Arousal: {state['arousal']:.2f}, Dominance: {state['dominance']:.2f}, Primary emotion: {state['primary_emotion']}"

    def generate_rumination_update(self, sensory_input, llm_response):
        """Generate a rumination update for a past sensory input"""
        try:
            # Wait a bit before ruminating
            rumination_delay = self.llm_config.get('rumination_delay', 15)
            time.sleep(rumination_delay)
            
            # Check if the original analysis had a significant impact
            changes = llm_response.get('changes', {})
            impact = abs(float(changes.get('pleasure_delta', 0.0))) + \
                    abs(float(changes.get('arousal_delta', 0.0))) + \
                    abs(float(changes.get('dominance_delta', 0.0)))
            
            # Only ruminate on impactful events
            if impact < 0.3:
                self.get_logger().debug(f'ALAINA: Skipping rumination for low-impact event (impact={impact:.2f})')
                return
            
            self.get_logger().info(f'ALAINA: Ruminating on past input: {sensory_input.description}')
            
            # Create a new rumination input
            rumination_input = SensoryInput()
            rumination_input.header = Header()
            rumination_input.header.stamp = self.get_clock().now().to_msg()
            rumination_input.input_id = f"rumination_{sensory_input.input_id}"
            rumination_input.input_type = "rumination"
            rumination_input.description = f"Ruminating on: {sensory_input.description}"
            rumination_input.confidence = 1.0
            rumination_input.intensity = sensory_input.intensity * 0.7  # Reduced intensity for rumination
            
            # Set metadata with the original input
            metadata = {
                'original_input_id': sensory_input.input_id,
                'original_input_type': sensory_input.input_type,
                'original_description': sensory_input.description,
                'original_analysis': llm_response.get('analysis', ''),
                'original_response': llm_response.get('emotional_response', '')
            }
            rumination_input.metadata = json.dumps(metadata)
            
            # Queue the rumination input
            self.input_queue.append(rumination_input)
            
        except Exception as e:
            self.get_logger().error(f'ALAINA: Error generating rumination: {str(e)}')
    
    def publish_emotion_vector(self):
        """Publish the current emotional state as a vector"""
        msg = Float32MultiArray()
        
        # Basic PAD model: joy, sadness, anger, fear, disgust, surprise, trust, anticipation
        # We'll derive these from the PAD values
        p = self.emotional_state['pleasure']
        a = self.emotional_state['arousal']
        d = self.emotional_state['dominance']
        
        # Simple mapping from PAD to basic emotions
        # These are approximate and could be improved
        joy = max(0, min(1, (p + 0.5 * a + 0.5 * d) / 2))
        sadness = max(0, min(1, (-p - 0.5 * a - 0.5 * d) / 2))
        anger = max(0, min(1, (-p + 0.5 * a + 0.5 * d) / 2))
        fear = max(0, min(1, (-p + 0.5 * a - 0.5 * d) / 2))
        disgust = max(0, min(1, (-p - 0.2 * a + 0.2 * d) / 1.4))
        surprise = max(0, min(1, (0.5 + 0.5 * a) / 1.5))
        trust = max(0, min(1, (p - 0.2 * a + 0.5 * d) / 1.7))
        anticipation = max(0, min(1, (0.2 * p + 0.5 * a + 0.3 * d) / 1))
        
        # Set the vector data
        msg.data = [joy, sadness, anger, fear, disgust, surprise, trust, anticipation]
        
        # Publish the vector
        self.emotion_vector_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = LLMIntegration()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f'ALAINA: Unexpected error: {str(e)}')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 