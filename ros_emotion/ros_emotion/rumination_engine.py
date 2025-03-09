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
from ros_emotion.feature_flags_client import FeatureFlagsClient

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
        
        # Initialize feature flags client (with a smaller delay to avoid startup timing issues)
        self.get_logger().info("ALAINA: Initializing feature flags client in rumination engine")
        time.sleep(1.0)  # Small delay to ensure feature flags service is started
        self.feature_flags = FeatureFlagsClient(self)
        
        # Internal cache for feature flags when service is unreachable
        self._feature_flags_local_cache = {
            'rumination_enabled': True,
            'use_llm_for_rumination': False  # Default to not using LLM for rumination
        }
        
        # Initialize rumination state
        self.active_ruminations = {}
        self.rumination_lock = Lock()
        self.current_emotional_state = None
        self.max_active_ruminations = self.config.get('max_active_ruminations', 3)
        self.rumination_probability = self.config.get('rumination_probability', 0.3)
        self.recency_factor = self.config.get('recency_factor', 0.5)
        self.intensity_threshold = self.config.get('intensity_threshold', 0.5)
        self.rumination_check_interval = self.config.get('rumination_check_interval', 15.0)
        self.max_rumination_stages = self.config.get('max_rumination_stages', 4)
        self.rumination_decay_factor = self.config.get('rumination_decay_factor', 0.8)
        
        # LLM configuration
        self.api_key = os.environ.get('OPENAI_API_KEY', '')
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
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
        
        # Create a periodic timer to ensure feature flags are refreshed periodically
        # This helps in case the feature flags service becomes available after initial startup
        self.feature_flags_refresh_timer = self.create_timer(
            30.0,  # Check every 30 seconds
            self.refresh_feature_flags,
            callback_group=callback_group
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
    
    def refresh_feature_flags(self):
        """Periodically refresh feature flags to ensure we have the latest values"""
        try:
            # Attempt to refresh the flags cache
            success = self.feature_flags.refresh_cache()
            if success:
                self.get_logger().debug("ALAINA: Successfully refreshed feature flags cache")
                # Update our local cache with the service values
                self._feature_flags_local_cache['rumination_enabled'] = self.feature_flags.is_feature_enabled(
                    'rumination_enabled', default=True)
                self._feature_flags_local_cache['use_llm_for_rumination'] = self.feature_flags.is_feature_enabled(
                    'use_llm_for_rumination', default=False)
            else:
                self.get_logger().debug("ALAINA: Failed to refresh feature flags cache")
        except Exception as e:
            self.get_logger().warn(f"ALAINA: Error refreshing feature flags: {str(e)}")
    
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
        # First check if rumination is enabled (with a fallback value)
        # Use a long default timeout for the first check
        is_rumination_enabled = self.feature_flags.is_feature_enabled('rumination_enabled', default=True)
        
        # If rumination is disabled, conclude all active ruminations
        if not is_rumination_enabled:
            with self.rumination_lock:
                rumination_ids = list(self.active_ruminations.keys())
                if rumination_ids:
                    self.get_logger().info(f"ALAINA: Rumination is disabled, concluding {len(rumination_ids)} active ruminations")
                
            for rum_id in rumination_ids:
                self.conclude_rumination(rum_id, "Rumination has been disabled")
                
            return
            
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
                self.conclude_rumination(rum_id, "Rumination has concluded naturally")
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
        # Check max stages
        if rumination["stage"] >= self.max_rumination_stages:
            return False
        
        # Check intensity decay
        if rumination["intensity"] < 0.2:  # Stop if intensity is too low
            return False
        
        # Check if a specific event should terminate the rumination
        if "should_terminate" in rumination and rumination["should_terminate"]:
            return False
        
        # Check if rumination is disabled
        if not self.feature_flags.is_feature_enabled('rumination_enabled', default=True):
            return False
        
        # Check if enough time has passed
        current_time = time.time()
        elapsed_time = current_time - rumination["start_time"]
        
        # Random chance to naturally conclude rumination increases with time
        termination_probability = 0.1 + (elapsed_time / 300.0) * 0.4  # Max 50% after 5 minutes
        if random.random() < termination_probability:
            return False
        
        return True
    
    def update_rumination(self, rum_id, rumination):
        """Update a rumination process"""
        try:
            # Check again if rumination is enabled (could have changed mid-process)
            if not self.feature_flags.is_feature_enabled('rumination_enabled', default=True):
                self.conclude_rumination(rum_id, "Rumination has been disabled")
                return
                
            # Prepare the rumination message for update
            rumination_msg = rumination["rumination_msg"]
            
            # Increment the stage
            new_stage = rumination["stage"] + 1
            rumination["stage"] = new_stage
            
            # Update intensity with decay
            new_intensity = rumination["intensity"] * self.rumination_decay_factor
            rumination["intensity"] = new_intensity
            
            # Update the message
            rumination_msg.rumination_stage = new_stage
            rumination_msg.intensity = new_intensity
            
            # Calculate elapsed time
            elapsed_time = time.time() - rumination["start_time"]
            duration = utils.create_duration(seconds=elapsed_time)
            rumination_msg.elapsed_time = duration
            
            # Query the LLM for the next stage of rumination
            self.get_logger().info(f"ALAINA: Calling LLM for rumination {rum_id} stage {new_stage}")
            llm_data = self.query_llm_for_rumination(rumination_msg, rum_id)
            
            if llm_data:
                # Create an emotional response from the LLM data
                self.create_emotional_response(llm_data, rum_id, rumination_msg)
                
                # Update the emotional state
                self.update_emotional_state(llm_data, rum_id)
                
                # Update the rumination message with new data
                rumination_msg.description = llm_data.get("rumination_text", "Continuing to ruminate...")
            else:
                # If LLM fails, use a default message
                rumination_msg.description = f"Ruminating on {rumination_msg.primary_emotion} state."
            
            # Publish the updated rumination message
            self.rumination_publisher.publish(rumination_msg)
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error updating rumination: {str(e)}")
            
            # On error, gently conclude the rumination
            self.conclude_rumination(rum_id, "Rumination terminated due to an error")
    
    def consider_new_rumination(self):
        """Consider starting a new rumination process"""
        # Check if rumination is enabled
        if not self.feature_flags.is_feature_enabled('rumination_enabled', default=True):
            return
            
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
        # Final check if rumination is enabled
        if not self.feature_flags.is_feature_enabled('rumination_enabled', default=True):
            return
            
        if not self.current_emotional_state:
            return
        
        # Generate a unique ID for this rumination
        rum_id = str(uuid.uuid4())
        
        # Get current emotional state primary emotion for rumination
        primary_emotion = self.current_emotional_state.primary_emotion
        overall_intensity = self.current_emotional_state.intensity
        
        # Check if emotional intensity is enough to trigger rumination
        if overall_intensity < self.intensity_threshold:
            return
        
        # Create a new rumination update message
        rumination_msg = RuminationUpdate()
        rumination_msg.timestamp = utils.get_current_time()
        rumination_msg.original_input_id = rum_id
        rumination_msg.rumination_stage = 0
        rumination_msg.elapsed_time = utils.create_duration(seconds=0.0)
        rumination_msg.intensity = overall_intensity
        rumination_msg.pleasure_change = 0.0
        rumination_msg.arousal_change = 0.0
        rumination_msg.dominance_change = 0.0
        rumination_msg.happiness_change = 0.0
        rumination_msg.sadness_change = 0.0
        rumination_msg.anger_change = 0.0
        rumination_msg.fear_change = 0.0
        rumination_msg.disgust_change = 0.0
        rumination_msg.surprise_change = 0.0
        rumination_msg.description = f"Beginning to ruminate on {primary_emotion} state."
        rumination_msg.is_final = False
        
        # Store the rumination in active ruminations
        with self.rumination_lock:
            self.active_ruminations[rum_id] = {
                "rumination_msg": rumination_msg,
                "start_time": time.time(),
                "stage": 0,
                "intensity": overall_intensity,
                "primary_emotion": primary_emotion
            }
        
        # Publish the initial rumination update
        self.rumination_publisher.publish(rumination_msg)
        self.get_logger().info(f"ALAINA: Started new rumination process {rum_id}")
    
    def query_llm_for_rumination(self, rumination_msg, rum_id):
        """Query the LLM to process a rumination update"""
        try:
            # Check if LLM for rumination is enabled (use local cache if service unavailable)
            use_llm = False
            try:
                use_llm = self.feature_flags.is_feature_enabled('use_llm_for_rumination', default=False)
            except Exception:
                # Fall back to local cache if service call fails
                use_llm = self._feature_flags_local_cache.get('use_llm_for_rumination', False)
            
            if not use_llm:
                self.get_logger().info(f"ALAINA: Skipping LLM call for rumination {rum_id} - feature disabled")
                
                # Get the primary emotion from the current emotional state
                primary_emotion = "neutral"
                if self.current_emotional_state:
                    primary_emotion = self.current_emotional_state.primary_emotion
                
                # Create a simple default response without using LLM
                default_data = {
                    "rumination_text": f"Ruminating on {primary_emotion} (LLM disabled).",
                    "emotional_impact": {
                        "pleasure": 0.0,
                        "arousal": 0.0,
                        "dominance": 0.0,
                        "primary_emotion": primary_emotion
                    },
                    "should_continue": rumination_msg.rumination_stage < (self.max_rumination_stages - 1)
                }
                
                # Create an emotional response from the default data
                self.create_emotional_response(default_data, rum_id, rumination_msg)
                return
            
            # Build prompt
            prompt = self.build_rumination_prompt(rumination_msg)
            
            # Call LLM API
            self.get_logger().info(f"ALAINA: Calling LLM for rumination {rum_id} stage {rumination_msg.rumination_stage}")
            response_text = self.call_llm_api(prompt)
            
            if not response_text:
                self.get_logger().error(f"ALAINA: Empty response from LLM for rumination {rum_id}")
                return None
            
            # Parse the response
            llm_data = self.parse_llm_response(response_text)
            if llm_data:
                # Create an emotional response from the LLM data
                self.create_emotional_response(llm_data, rum_id, rumination_msg)
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error querying LLM for rumination: {str(e)}")
            # Add traceback for more detailed error information
            import traceback
            self.get_logger().error(f"ALAINA: Traceback: {traceback.format_exc()}")
    
    def build_rumination_prompt(self, rumination_msg):
        """Build a prompt for rumination"""
        
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
        
        # Build the prompt for the user message
        prompt = f"""I need you to simulate the internal rumination process of a robot with the following personality and emotional state.

PERSONALITY PROFILE:
{personality_context}

CURRENT EMOTIONAL STATE:
{json.dumps(current_state, indent=2)}

RUMINATION STAGE:
Stage: {rumination_msg.rumination_stage} of {self.max_rumination_stages}
Elapsed time: {rumination_msg.elapsed_time.sec} seconds
Intensity: {rumination_msg.intensity}
Current rumination description: {rumination_msg.description}
"""

        # Add previous rumination stages if available
        if previous_stages:
            prompt += "\nPREVIOUS RUMINATION STAGES:\n"
            for i, stage in enumerate(previous_stages):
                prompt += f"Stage {i}: {stage}\n"
        
        # Add instructions for the response format
        prompt += """
Based on the personality traits and current emotional state, create the next rumination stage. 
Consider how the robot would reflect on its current emotional state internally.

Respond with a JSON object in the following format:
```json
{
  "rumination_text": "The internal thought process of the robot as it ruminates on its current emotional state",
  "emotional_impact": {
    "pleasure": float (-0.2 to 0.2), 
    "arousal": float (-0.2 to 0.2), 
    "dominance": float (-0.2 to 0.2),
    "primary_emotion": "happiness|sadness|anger|fear|disgust|surprise"
  },
  "should_continue": boolean (whether rumination should continue to next stage)
}
```

Important considerations for this rumination stage:
- Match the personality traits in your response (e.g., neurotic personalities ruminate more negatively)
- The emotional impact values should be small deltas (changes), not absolute values
- Use the current emotional state as a starting point for your rumination
- Make the rumination process feel natural and evolving
- The intensity of the rumination should gradually decrease with each stage
"""
        
        return prompt
    
    def call_llm_api(self, prompt):
        """Call the LLM API with the given prompt"""
        try:
            if not self.api_key:
                self.get_logger().error("ALAINA: Cannot call OpenAI API: API key not set")
                return None
            
            # Create request payload for OpenAI
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are the rumination process of a robot with a specific personality."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"}
            }
            
            # Add API key to headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Set longer timeout for API call
            timeout = 30.0  # 30 seconds
            
            # Log API request details (excluding the actual API key)
            self.get_logger().debug(f"ALAINA: Calling OpenAI API with model {self.model} at {self.api_url}")
            
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
            
            # Extract content from OpenAI response
            if "choices" in response_json and len(response_json["choices"]) > 0:
                return response_json["choices"][0]["message"]["content"]
            else:
                self.get_logger().error(f"ALAINA: Unexpected OpenAI API response format: {response_json}")
                return None
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error calling OpenAI API: {str(e)}")
            # Add traceback for more detailed error information
            import traceback
            self.get_logger().error(f"ALAINA: Traceback: {traceback.format_exc()}")
            return None
    
    def create_emotional_response(self, data, rum_id, rumination_msg):
        """Create an emotional response from LLM data"""
        try:
            # Create a new emotional response message
            response = EmotionalResponse()
            
            # Set timestamp
            response.timestamp = utils.get_current_time()
            
            # Set stimulus ID
            response.stimulus_id = rum_id
            
            # Set rumination flag
            response.is_rumination = True
            
            # Set response text from rumination text
            response.response_text = data.get("rumination_text", "Continuing to ruminate...")
            
            # Set source
            response.source = "rumination"
            
            # Set previous state (current state before update)
            response.previous_state = utils.copy_emotional_state(self.current_emotional_state)
            
            # Extract emotional impact
            emotional_impact = data.get("emotional_impact", {})
            
            # Copy deltas from emotional impact
            response.pleasure_delta = emotional_impact.get("pleasure", 0.0)
            response.arousal_delta = emotional_impact.get("arousal", 0.0)
            response.dominance_delta = emotional_impact.get("dominance", 0.0)
            
            # Set primary emotion
            response.primary_emotion = emotional_impact.get("primary_emotion", response.previous_state.primary_emotion)
            
            # Calculate intensity based on rumination stage and original intensity
            stage_factor = 1.0 - (rumination_msg.rumination_stage / self.max_rumination_stages) * 0.5
            response.intensity = rumination_msg.intensity * stage_factor
            response.intensity = utils.clamp(response.intensity, 0.0, 1.0)
            
            # Set confidence (relatively high for rumination)
            response.confidence = 0.8
            
            # Create metadata
            metadata = {
                "rumination_stage": rumination_msg.rumination_stage,
                "elapsed_time": rumination_msg.elapsed_time.sec,
                "should_continue": data.get("should_continue", True),
                "process_time": time.time()
            }
            response.metadata = json.dumps(metadata)
            
            # Check if we should terminate this rumination
            with self.rumination_lock:
                if rum_id in self.active_ruminations:
                    # Store the should_continue flag to be checked in should_continue_rumination
                    self.active_ruminations[rum_id]["should_terminate"] = not data.get("should_continue", True)
                    
                    # Store the response for future reference
                    if "previous_responses" not in self.active_ruminations[rum_id]:
                        self.active_ruminations[rum_id]["previous_responses"] = []
                    self.active_ruminations[rum_id]["previous_responses"].append(data.get("rumination_text", ""))
            
            # Publish the emotional response
            self.response_publisher.publish(response)
            
            # Update emotional state
            self.update_emotional_state(data, rum_id)
            
            return response
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error creating emotional response: {str(e)}")
            return None
    
    def update_emotional_state(self, llm_data, rum_id):
        """Update the emotional state based on LLM data"""
        try:
            # Wait for service to be available with a short timeout
            if not self.emotion_modify_client.wait_for_service(timeout_sec=1.0):
                self.get_logger().warn("ALAINA: Emotion modify service not available")
                return False
            
            # Extract emotional impact
            emotional_impact = llm_data.get("emotional_impact", {})
            
            # Update pleasure
            pleasure_delta = emotional_impact.get("pleasure", 0.0)
            if pleasure_delta != 0.0:
                pleasure_request = EmotionModify.Request()
                pleasure_request.modification_type = "relative"
                pleasure_request.specific_emotion = "pleasure"
                pleasure_request.value = pleasure_delta
                pleasure_request.reason = f"Rumination {rum_id}"
                pleasure_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(pleasure_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, rum_id, "pleasure")
                )
            
            # Update arousal
            arousal_delta = emotional_impact.get("arousal", 0.0)
            if arousal_delta != 0.0:
                arousal_request = EmotionModify.Request()
                arousal_request.modification_type = "relative"
                arousal_request.specific_emotion = "arousal"
                arousal_request.value = arousal_delta
                arousal_request.reason = f"Rumination {rum_id}"
                arousal_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(arousal_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, rum_id, "arousal")
                )
            
            # Update dominance
            dominance_delta = emotional_impact.get("dominance", 0.0)
            if dominance_delta != 0.0:
                dominance_request = EmotionModify.Request()
                dominance_request.modification_type = "relative"
                dominance_request.specific_emotion = "dominance"
                dominance_request.value = dominance_delta
                dominance_request.reason = f"Rumination {rum_id}"
                dominance_request.override_safety = False
                
                # Send request
                future = self.emotion_modify_client.call_async(dominance_request)
                future.add_done_callback(
                    lambda f: self.emotion_modify_callback(f, rum_id, "dominance")
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
    
    def conclude_rumination(self, rum_id, conclusion_reason):
        """Conclude a rumination process."""
        self.get_logger().info(f"ALAINA: {conclusion_reason} on {rum_id}")
        
        with self.rumination_lock:
            if rum_id in self.active_ruminations:
                self.active_ruminations[rum_id]["rumination_msg"].is_final = True
                self.rumination_publisher.publish(self.active_ruminations[rum_id]["rumination_msg"])
                del self.active_ruminations[rum_id]

    def parse_llm_response(self, response_text):
        """Parse the LLM response text to extract structured data"""
        try:
            # OpenAI response should be a JSON string already with response_format=json_object
            data = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["rumination_text", "emotional_impact"]
            for field in required_fields:
                if field not in data:
                    self.get_logger().warn(f"ALAINA: Missing required field in LLM response: {field}")
                    # If emotional_impact is missing, add default values
                    if field == "emotional_impact":
                        data["emotional_impact"] = {
                            "pleasure": 0.0,
                            "arousal": 0.0,
                            "dominance": 0.0,
                            "primary_emotion": "neutral"
                        }
            
            # If response doesn't have an emotional_impact field, add defaults
            if not isinstance(data.get("emotional_impact"), dict):
                data["emotional_impact"] = {
                    "pleasure": 0.0,
                    "arousal": 0.0,
                    "dominance": 0.0,
                    "primary_emotion": "neutral"
                }
            
            return data
            
        except json.JSONDecodeError as e:
            self.get_logger().error(f"ALAINA: Error parsing LLM response as JSON: {str(e)}")
            # Fallback: try to extract JSON from text (in case there's extra text)
            try:
                import re
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                
                if json_match:
                    json_text = json_match.group(1)
                    return json.loads(json_text)
                else:
                    self.get_logger().error(f"ALAINA: Could not find JSON in LLM response: {response_text[:100]}...")
                    return None
            except Exception as e2:
                self.get_logger().error(f"ALAINA: Fallback JSON parsing failed: {str(e2)}")
                return None
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error parsing LLM response: {str(e)}")
            return None

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