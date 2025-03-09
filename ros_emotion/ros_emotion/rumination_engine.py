#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import RuminationUpdate, EmotionalState, EmotionalResponse, SensoryInput
from ros_emotion.srv import EmotionModify
import time
import uuid
import json
import random
import requests
import os
from threading import Lock
import ros_emotion.utils as utils
from ros_emotion.emotion_model import create_emotion_model
from ros_emotion.personality_model import create_personality_model
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

class RuminationEngine(Node):
    def __init__(self):
        super().__init__('rumination_engine')
        
        # Load configuration
        self.config = utils.load_config(self, 'emotion_config.yaml').get('rumination_engine', {})
        
        # Initialize the emotion model
        emotion_model_type = self.config.get('emotion_model_type', 'pad_basic')
        self.emotion_model = create_emotion_model(emotion_model_type)
        
        # Initialize the personality model
        personality_model_type = self.config.get('personality_model_type', 'hybrid')
        personality_config = self.config.get('personality', {})
        self.personality_model = create_personality_model(personality_model_type, personality_config)
        
        # Initialize rumination state
        self.active_ruminations = {}
        self.rumination_lock = Lock()
        self.current_emotional_state = None
        self.max_active_ruminations = self.config.get('max_active_ruminations', 3)
        self.rumination_probability = self.config.get('rumination_probability', 0.3)
        self.recency_factor = self.config.get('recency_factor', 0.5)
        self.intensity_threshold = self.config.get('intensity_threshold', 0.5)
        self.rumination_check_interval = self.config.get('rumination_check_interval', 10.0)
        self.max_rumination_stages = self.config.get('max_rumination_stages', 3)
        self.rumination_decay_factor = self.config.get('rumination_decay_factor', 0.8)
        
        # LLM configuration
        self.api_key = os.environ.get('LLM_API_KEY', 'demo-key')
        self.api_url = self.config.get('api_url', 'http://localhost:8000/api/chat')
        self.model = self.config.get('model', 'gpt-3.5-turbo')
        self.max_tokens = self.config.get('max_tokens', 1024)
        self.temperature = self.config.get('temperature', 0.7)
        
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
        
        # Subscribe to rumination updates to avoid re-ruminating on active topics
        self.rumination_sub = self.create_subscription(
            RuminationUpdate,
            'rumination_update',
            self.rumination_callback,
            qos,
            callback_group=callback_group
        )
        
        # Create publishers
        self.rumination_publisher = self.create_publisher(
            RuminationUpdate,
            'rumination_update',
            10
        )
        
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
        
        # Create timer for rumination processing
        self.rumination_timer = self.create_timer(
            1.0,
            self.process_ruminations,
            callback_group=callback_group
        )
        
        # Timers for new rumination consideration
        self.new_rumination_timer = self.create_timer(
            self.rumination_check_interval,
            self.consider_new_rumination, 
            callback_group=callback_group
        )
        
        # Track last rumination time
        self.last_rumination_time = time.time()
        
        self.get_logger().info("ALAINA: Rumination Engine initialized")
        self.get_logger().info(f"ALAINA: Using personality model: {personality_model_type}")
        self.get_logger().debug(f"ALAINA: Personality traits: {self.personality_model.format_personality_traits()}")
    
    def emotional_state_callback(self, msg):
        """Store the current emotional state"""
        self.current_emotional_state = msg
    
    def rumination_callback(self, msg):
        """Handle incoming rumination updates"""
        self.get_logger().debug(f"ALAINA: Received rumination update for {msg.original_input_id}")
        
        # If this is a final update, remove from active ruminations
        if msg.is_final:
            with self.rumination_lock:
                if msg.original_input_id in self.active_ruminations:
                    del self.active_ruminations[msg.original_input_id]
                    self.get_logger().info(f"ALAINA: Completed rumination on {msg.original_input_id}")
    
    def process_ruminations(self):
        """Process active ruminations"""
        if not self.current_emotional_state:
            return
        
        with self.rumination_lock:
            # Get a copy of keys to avoid modification during iteration
            rumination_ids = list(self.active_ruminations.keys())
            
        for rum_id in rumination_ids:
            with self.rumination_lock:
                if rum_id not in self.active_ruminations:
                    continue
                rumination = self.active_ruminations[rum_id]
            
            # Check if we should continue this rumination
            if not self.should_continue_rumination(rumination):
                # Create a final update
                rumination["rumination_msg"].is_final = True
                rumination["rumination_msg"].description = "Rumination has concluded naturally."
                
                # Publish final update
                self.rumination_publisher.publish(rumination["rumination_msg"])
                
                # Remove from active ruminations
                with self.rumination_lock:
                    del self.active_ruminations[rum_id]
                
                self.get_logger().info(f"ALAINA: Naturally concluded rumination on {rum_id}")
                continue
            
            # Update this rumination
            self.update_rumination(rum_id, rumination)
        
        # Log current rumination status periodically
        if random.random() < 0.05:  # ~5% chance each call
            with self.rumination_lock:
                num_active = len(self.active_ruminations)
            self.get_logger().debug(f"ALAINA: Currently {num_active} active ruminations")
    
    def should_continue_rumination(self, rumination):
        """Determine if a rumination should continue"""
        # Check if we've reached the maximum rumination stages
        if rumination["stage"] >= self.max_rumination_stages:
            return False
        
        # Check if the rumination has decayed below threshold
        intensity = rumination["rumination_msg"].intensity
        if intensity < self.intensity_threshold / 2.0:
            return False
        
        # Apply personality influence to continuation decision
        # Neurotic personalities tend to ruminate more
        neuroticism = self.personality_model.get_trait_value("neuroticism")
        # Higher neuroticism means higher chance of continuing rumination
        neuroticism_factor = 1.0 + (neuroticism - 0.5) * 0.6
        
        # Conscientious personalities may limit unhelpful rumination
        conscientiousness = self.personality_model.get_trait_value("conscientiousness")
        # Higher conscientiousness means lower chance of continuing negative rumination
        if rumination.get("valence", 0) < 0:  # Negative rumination
            conscientiousness_factor = 1.0 - (conscientiousness - 0.5) * 0.4
        else:
            conscientiousness_factor = 1.0  # No effect on positive rumination
        
        # Calculate continuation probability based on personality
        continuation_probability = 0.7 * neuroticism_factor * conscientiousness_factor
        
        # Apply random chance with personality-influenced probability
        return random.random() < continuation_probability
    
    def update_rumination(self, rum_id, rumination):
        """Update a rumination process"""
        try:
            # Increment the stage
            rumination["stage"] += 1
            
            # Update the rumination message
            msg = rumination["rumination_msg"]
            msg.rumination_stage = rumination["stage"]
            
            # Calculate elapsed time
            elapsed_seconds = time.time() - rumination["start_time"]
            msg.elapsed_time = utils.create_duration(elapsed_seconds)
            
            # Decay the intensity
            msg.intensity *= self.rumination_decay_factor
            
            # Adjust the intensity based on personality (neuroticism and extraversion)
            neuroticism = self.personality_model.get_trait_value("neuroticism")
            extraversion = self.personality_model.get_trait_value("extraversion")
            
            # Higher neuroticism prolongs rumination intensity
            neuroticism_factor = 1.0 + (neuroticism - 0.5) * 0.4
            # Higher extraversion reduces negative rumination intensity, increases positive
            if rumination.get("valence", 0) < 0:  # Negative rumination
                extraversion_factor = 1.0 - (extraversion - 0.5) * 0.2
            else:  # Positive rumination
                extraversion_factor = 1.0 + (extraversion - 0.5) * 0.2
            
            # Apply personality factors to intensity
            msg.intensity *= neuroticism_factor * extraversion_factor
            msg.intensity = utils.clamp(msg.intensity, 0.0, 1.0)
            
            # Query LLM for next stage of rumination
            self.query_llm_for_rumination(msg, rum_id)
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error updating rumination: {str(e)}")
            # In case of error, mark as final to avoid further processing
            with self.rumination_lock:
                if rum_id in self.active_ruminations:
                    self.active_ruminations[rum_id]["rumination_msg"].is_final = True
                    self.rumination_publisher.publish(self.active_ruminations[rum_id]["rumination_msg"])
                    del self.active_ruminations[rum_id]
    
    def consider_new_rumination(self):
        """Consider starting a new rumination process"""
        if not self.current_emotional_state:
            return
        
        with self.rumination_lock:
            # Check if we're already at max ruminations
            if len(self.active_ruminations) >= self.max_active_ruminations:
                return
            
        # Adjustment based on personality traits
        neuroticism = self.personality_model.get_trait_value("neuroticism")
        openness = self.personality_model.get_trait_value("openness")
        
        # Higher neuroticism increases rumination probability
        neuroticism_adjustment = (neuroticism - 0.5) * 0.3
        # Higher openness increases rumination probability (more reflective)
        openness_adjustment = (openness - 0.5) * 0.2
        
        # Adjust base probability
        adjusted_probability = self.rumination_probability + neuroticism_adjustment + openness_adjustment
        adjusted_probability = utils.clamp(adjusted_probability, 0.1, 0.8)
        
        # Random chance to start a new rumination
        if random.random() < adjusted_probability:
            self.start_new_rumination()
    
    def start_new_rumination(self):
        """Start a new rumination process"""
        if not self.current_emotional_state:
            return
        
        # Generate a unique ID for this rumination
        rum_id = str(uuid.uuid4())
        
        # Create a new rumination update message
        msg = RuminationUpdate()
        
        # Set timestamp
        msg.timestamp = utils.get_current_time()
        
        # Set original input ID
        msg.original_input_id = rum_id
        
        # Set rumination stage (initial stage)
        msg.rumination_stage = 0
        
        # Set elapsed time (just started)
        msg.elapsed_time = utils.create_duration(0.0)
        
        # Set intensity based on emotional state and personality
        intensity = self.current_emotional_state.intensity
        neuroticism = self.personality_model.get_trait_value("neuroticism")
        
        # Higher neuroticism increases starting intensity
        neuroticism_factor = 1.0 + (neuroticism - 0.5) * 0.4
        # Set starting intensity based on current emotional intensity and neuroticism
        msg.intensity = intensity * 0.8 * neuroticism_factor
        msg.intensity = utils.clamp(msg.intensity, 0.0, 1.0)
        
        # Initialize change values (will be set by LLM)
        msg.pleasure_change = 0.0
        msg.arousal_change = 0.0
        msg.dominance_change = 0.0
        msg.happiness_change = 0.0
        msg.sadness_change = 0.0
        msg.anger_change = 0.0
        msg.fear_change = 0.0
        msg.disgust_change = 0.0
        msg.surprise_change = 0.0
        
        # Set description
        msg.description = f"Beginning to ruminate on {self.current_emotional_state.primary_emotion} state."
        
        # This is the initial update, not final
        msg.is_final = False
        
        # Store the rumination
        with self.rumination_lock:
            self.active_ruminations[rum_id] = {
                "rumination_msg": msg,
                "stage": 0,
                "start_time": time.time(),
                "primary_emotion": self.current_emotional_state.primary_emotion,
                "valence": self.current_emotional_state.pleasure,  # Store valence for later use
            }
        
        # Publish the initial update
        self.rumination_publisher.publish(msg)
        
        # Update last rumination time
        self.last_rumination_time = time.time()
        
        self.get_logger().info(f"ALAINA: Started new rumination process {rum_id}")
        
        # Query LLM to start the rumination
        self.query_llm_for_rumination(msg, rum_id)
    
    def query_llm_for_rumination(self, rumination_msg, rum_id):
        """Query the LLM to process a rumination update"""
        try:
            # Build prompt
            prompt = self.build_rumination_prompt(rumination_msg)
            
            # Call LLM API
            self.get_logger().info(f"ALAINA: Calling LLM for rumination {rum_id} stage {rumination_msg.rumination_stage}")
            response_text = self.call_llm_api(prompt)
            
            if not response_text:
                self.get_logger().error(f"ALAINA: Empty response from LLM for rumination {rum_id}")
                return
            
            # Parse the response
            try:
                import re
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                
                if json_match:
                    json_text = json_match.group(1)
                    llm_data = json.loads(json_text)
                    
                    # Create an emotional response from the LLM data
                    self.create_emotional_response(llm_data, rum_id, rumination_msg)
                    
                    # Update the emotional state
                    self.update_emotional_state(llm_data, rum_id)
                else:
                    self.get_logger().error(f"ALAINA: Could not parse LLM response: {response_text}")
            except Exception as e:
                self.get_logger().error(f"ALAINA: Error parsing LLM response: {str(e)}")
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error querying LLM for rumination: {str(e)}")
    
    def build_rumination_prompt(self, rumination_msg):
        """Build a prompt for the LLM to process rumination"""
        # Only build prompt if we have emotional state
        if not self.current_emotional_state:
            self.get_logger().warn("ALAINA: Cannot build rumination prompt - no emotional state")
            return "No emotional state available"
        
        # Format the current emotional state
        current_state = {}
        
        # Add dimensional values
        for dim in self.emotion_model.get_dimensions():
            current_state[dim] = self.emotion_model.get_emotion_value(self.current_emotional_state, dim)
        
        # Add basic emotion values
        for emotion in self.emotion_model.get_all_emotions():
            current_state[emotion] = self.emotion_model.get_emotion_value(self.current_emotional_state, emotion)
        
        # Add other state information
        current_state["intensity"] = self.current_emotional_state.intensity
        current_state["description"] = self.current_emotional_state.description
        current_state["primary_emotion"] = self.current_emotional_state.primary_emotion
        
        # Get personality traits and context
        personality_context = self.personality_model.get_llm_context()
        personality_traits = self.personality_model.get_all_traits()
        
        # Get previous rumination stages
        previous_stages = []
        with self.rumination_lock:
            if rumination_msg.original_input_id in self.active_ruminations:
                rumination = self.active_ruminations[rumination_msg.original_input_id]
                if "previous_responses" in rumination:
                    previous_stages = rumination["previous_responses"]
        
        # Build the prompt
        prompt = f"""You are the rumination process of a robot with a specific personality.
Given the current emotional state, personality profile, and rumination stage, simulate how the robot would ruminate on its emotions.

PERSONALITY PROFILE:
{personality_context}

CURRENT EMOTIONAL STATE:
{json.dumps(current_state, indent=2)}

RUMINATION INFORMATION:
Stage: {rumination_msg.rumination_stage} of {self.max_rumination_stages}
Elapsed time: {rumination_msg.elapsed_time.sec} seconds
Intensity: {rumination_msg.intensity}
Description: {rumination_msg.description}

"""

        # Add previous rumination stages if available
        if previous_stages:
            prompt += "PREVIOUS RUMINATION STAGES:\n"
            for i, stage in enumerate(previous_stages):
                prompt += f"Stage {i}: {stage.get('response_text', '')}\n"
            
        # Add personality-specific instructions
        neuroticism = self.personality_model.get_trait_value("neuroticism")
        openness = self.personality_model.get_trait_value("openness")
        extraversion = self.personality_model.get_trait_value("extraversion")
        
        prompt += f"""
Based on this information, and considering the personality traits (especially neuroticism at {neuroticism:.2f}),
simulate how the robot would ruminate on its current emotional state:

1. How would the rumination process evolve at this stage?
2. How would this rumination affect the emotional state?
3. What thoughts would occur during this rumination?

IMPORTANT CONSIDERATIONS:
- {'Highly neurotic personalities tend to amplify negative emotions through rumination' if neuroticism > 0.7 else 'Low neuroticism personalities tend to process emotions more evenly'}
- {'High openness leads to more abstract and philosophical rumination' if openness > 0.7 else 'Low openness leads to more concrete and practical rumination'}
- {'Extraverted personalities ruminate less on negative emotions' if extraversion > 0.7 else 'Introverted personalities may dwell longer on internal emotional states'}
- As rumination stages progress, the intensity should generally decrease
- Later stages often lead to resolution or acceptance

Respond ONLY with a valid JSON object in the following format:
{{
  "pleasure_change": float (-0.3 to 0.3),
  "arousal_change": float (-0.3 to 0.3),
  "dominance_change": float (-0.3 to 0.3),
  "happiness_change": float (-0.2 to 0.2),
  "sadness_change": float (-0.2 to 0.2),
  "anger_change": float (-0.2 to 0.2),
  "fear_change": float (-0.2 to 0.2),
  "disgust_change": float (-0.2 to 0.2),
  "surprise_change": float (-0.2 to 0.2),
  "intensity": float (0.0 to 1.0),
  "is_final": boolean,
  "response_text": string (the rumination thoughts and process),
  "description": string (short summary for the rumination update)
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
    
    def create_emotional_response(self, data, rum_id, rumination_msg):
        """Create an emotional response from LLM data"""
        try:
            # Create a new emotional response message
            response = EmotionalResponse()
            
            # Set timestamp
            response.timestamp = utils.get_current_time()
            
            # Set stimulus ID to the rumination ID
            response.stimulus_id = rum_id
            
            # This is a rumination response
            response.is_rumination = True
            
            # Set response text
            response.response_text = data.get("response_text", "")
            
            # Set source
            response.source = "rumination"
            
            # Set previous state (current state before update)
            response.previous_state = utils.copy_emotional_state(self.current_emotional_state)
            
            # Copy deltas from LLM response
            response.pleasure_delta = data.get("pleasure_change", 0.0)
            response.arousal_delta = data.get("arousal_change", 0.0)
            response.dominance_delta = data.get("dominance_change", 0.0)
            
            # Determine primary emotion (could be calculated based on changes)
            emotions = self.emotion_model.get_all_emotions()
            emotion_changes = {
                e: data.get(f"{e}_change", 0.0) for e in emotions
            }
            # Primary emotion is the one with the largest absolute change
            primary_emotion = max(emotion_changes.items(), key=lambda x: abs(x[1]))
            response.primary_emotion = primary_emotion[0]
            
            # Set intensity
            response.intensity = data.get("intensity", rumination_msg.intensity)
            
            # Confidence is medium for rumination
            response.confidence = 0.7
            
            # Create metadata
            metadata = {
                "rumination_stage": rumination_msg.rumination_stage,
                "elapsed_time": rumination_msg.elapsed_time.sec,
                "is_final": data.get("is_final", False),
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
            
            # Store the response data for future reference
            with self.rumination_lock:
                if rum_id in self.active_ruminations:
                    if "previous_responses" not in self.active_ruminations[rum_id]:
                        self.active_ruminations[rum_id]["previous_responses"] = []
                    self.active_ruminations[rum_id]["previous_responses"].append(data)
            
            # Update the rumination message with the LLM data
            rumination_msg.pleasure_change = modulated_response.pleasure_delta
            rumination_msg.arousal_change = modulated_response.arousal_delta
            rumination_msg.dominance_change = modulated_response.dominance_delta
            
            # Update specific emotion changes
            rumination_msg.happiness_change = data.get("happiness_change", 0.0)
            rumination_msg.sadness_change = data.get("sadness_change", 0.0)
            rumination_msg.anger_change = data.get("anger_change", 0.0)
            rumination_msg.fear_change = data.get("fear_change", 0.0)
            rumination_msg.disgust_change = data.get("disgust_change", 0.0)
            rumination_msg.surprise_change = data.get("surprise_change", 0.0)
            
            # Update description
            rumination_msg.description = data.get("description", rumination_msg.description)
            
            # Update is_final flag
            rumination_msg.is_final = data.get("is_final", False)
            
            # Publish the updated rumination message
            self.rumination_publisher.publish(rumination_msg)
            
            return modulated_response
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error creating emotional response: {str(e)}")
            return None
    
    def update_emotional_state(self, llm_data, rum_id):
        """Update the emotional state through service calls"""
        # Wait for service to be available
        if not self.emotion_modify_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("ALAINA: Emotion modify service not available")
            return False
        
        try:
            # Apply personality modulation to the changes
            neuroticism = self.personality_model.get_trait_value("neuroticism")
            # Higher neuroticism amplifies emotional changes from rumination
            neuroticism_factor = 1.0 + (neuroticism - 0.5) * 0.4
            
            # Create request for pleasure
            pleasure_change = llm_data.get("pleasure_change", 0.0) * neuroticism_factor
            if abs(pleasure_change) > 0.01:
                pleasure_request = EmotionModify.Request()
                pleasure_request.modification_type = "relative"
                pleasure_request.specific_emotion = "pleasure"
                pleasure_request.value = pleasure_change
                pleasure_request.reason = f"Rumination {rum_id}"
                pleasure_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(pleasure_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, rum_id, "pleasure")
                )
            
            # Create request for arousal
            arousal_change = llm_data.get("arousal_change", 0.0) * neuroticism_factor
            if abs(arousal_change) > 0.01:
                arousal_request = EmotionModify.Request()
                arousal_request.modification_type = "relative"
                arousal_request.specific_emotion = "arousal"
                arousal_request.value = arousal_change
                arousal_request.reason = f"Rumination {rum_id}"
                arousal_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(arousal_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, rum_id, "arousal")
                )
            
            # Create request for dominance
            dominance_change = llm_data.get("dominance_change", 0.0) * neuroticism_factor
            if abs(dominance_change) > 0.01:
                dominance_request = EmotionModify.Request()
                dominance_request.modification_type = "relative"
                dominance_request.specific_emotion = "dominance"
                dominance_request.value = dominance_change
                dominance_request.reason = f"Rumination {rum_id}"
                dominance_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(dominance_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, rum_id, "dominance")
                )
            
            # Create requests for basic emotions
            for emotion in ["happiness", "sadness", "anger", "fear", "disgust", "surprise"]:
                change_field = f"{emotion}_change"
                if change_field in llm_data:
                    change = llm_data[change_field] * neuroticism_factor
                    if abs(change) > 0.01:
                        request = EmotionModify.Request()
                        request.modification_type = "relative"
                        request.specific_emotion = emotion
                        request.value = change
                        request.reason = f"Rumination {rum_id}"
                        request.override_safety = False
                        
                        # Send request
                        future = self.emotion_modify_client.call_async(request)
                        future.add_done_callback(
                            lambda f, e=emotion: self.emotion_modify_callback(f, rum_id, e)
                        )
            
            return True
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error updating emotional state: {str(e)}")
            return False
    
    def emotion_modify_callback(self, future, rum_id, emotion_type):
        """Callback for emotion modify service"""
        try:
            response = future.result()
            if response.success:
                self.get_logger().debug(f"ALAINA: Successfully updated {emotion_type} for rumination {rum_id}")
            else:
                self.get_logger().warn(f"ALAINA: Failed to update {emotion_type} for rumination {rum_id}: {response.error_message}")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error in emotion modify callback: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    
    node = RuminationEngine()
    
    # Use a MultiThreadedExecutor to enable processing concurrent callbacks
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info("ALAINA: Shutting down Rumination Engine node")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 