#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import RuminationUpdate, EmotionalState, EmotionalResponse
from ros_emotion.srv import EmotionModify
import random
import time
import json
import copy
import uuid
import ros_emotion.utils as utils
from ros_emotion.emotion_model import create_emotion_model

class RuminationEngine(Node):
    def __init__(self):
        super().__init__('rumination_engine')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.rumination_config = self.config.get('rumination_engine', {})
        
        # Create emotion model
        model_type = self.config.get('emotion_model', {}).get('type', 'pad_basic')
        self.emotion_model = create_emotion_model(model_type, self.config.get('emotion_model', {}))
        self.get_logger().info(f"ALAINA: Created emotion model of type {model_type}")
        
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
        self.rumination_sub = self.create_subscription(
            RuminationUpdate,
            'rumination_update',
            self.rumination_callback,
            qos
        )
        
        self.emotional_state_sub = self.create_subscription(
            EmotionalState,
            'emotional_state',
            self.emotional_state_callback,
            qos
        )
        
        # Create service client for emotion modification
        self.emotion_modify_client = self.create_client(
            EmotionModify,
            '/modify_emotional_state'
        )
        
        # Active ruminations
        self.active_ruminations = {}
        
        # Current emotional state
        self.current_emotional_state = EmotionalState()
        
        # Configuration parameters
        self.max_active_ruminations = self.rumination_config.get('max_active_ruminations', 3)
        self.stages = self.rumination_config.get('stages', 5)
        self.update_interval = self.rumination_config.get('update_interval', 5.0)
        self.continuation_probability = self.rumination_config.get('continuation_probability', 0.8)
        self.intensity_decay = self.rumination_config.get('intensity_decay', 0.1)
        
        # LLM API settings
        self.rumination_timer = self.create_timer(self.update_interval, self.process_ruminations)
        self.last_rumination_time = time.time()
        
        self.get_logger().info("Rumination Engine initialized")
    
    def emotional_state_callback(self, msg):
        """Store the current emotional state"""
        self.current_emotional_state = msg
        self.get_logger().debug("Updated emotional state")
    
    def rumination_callback(self, msg):
        """Process incoming rumination updates"""
        # Only handle external updates
        if msg.original_input_id in self.active_ruminations:
            # This is our own update, ignore
            return
            
        # Store or update in active ruminations
        self.active_ruminations[msg.original_input_id] = {
            'stage': msg.rumination_stage,
            'intensity': msg.intensity,
            'subject': msg.description,
            'last_update': time.time(),
            'message': msg
        }
        
        self.get_logger().info(f"ALAINA: Received external rumination: {msg.original_input_id}")
    
    def process_ruminations(self):
        """Process active ruminations and potentially trigger state changes"""
        current_time = time.time()
        
        # Only run processing if minimum interval has passed
        if current_time - self.last_rumination_time < self.update_interval:
            return
        
        self.last_rumination_time = current_time
        
        if not self.active_ruminations:
            # If no ruminations, consider starting one based on current emotional state
            self.consider_new_rumination()
            return
            
        # Process each active rumination
        ruminations_to_remove = []
        
        for rum_id, rumination in self.active_ruminations.items():
            # Skip if recently updated
            if current_time - rumination['last_update'] < self.update_interval:
                continue
                
            # Determine if this rumination continues or ends
            if self.should_continue_rumination(rumination):
                # Update the rumination
                self.update_rumination(rum_id, rumination)
            else:
                # End this rumination
                self.get_logger().info(f"ALAINA: Ending rumination {rum_id}")
                ruminations_to_remove.append(rum_id)
        
        # Remove completed ruminations
        for rum_id in ruminations_to_remove:
            del self.active_ruminations[rum_id]
    
    def should_continue_rumination(self, rumination):
        """Determine if a rumination should continue"""
        # Check if max stages reached
        if rumination['stage'] >= self.stages:
            return False
            
        # Check intensity threshold
        if rumination['intensity'] < 0.1:
            return False
            
        # Apply continuation probability
        return random.random() < self.continuation_probability
    
    def update_rumination(self, rum_id, rumination):
        """Update a rumination to the next stage"""
        # Increment stage
        rumination['stage'] += 1
        
        # Reduce intensity slightly
        rumination['intensity'] = max(0.0, rumination['intensity'] - self.intensity_decay)
        
        # Create updated rumination message
        msg = copy.deepcopy(rumination['message'])
        msg.rumination_stage = rumination['stage']
        msg.intensity = rumination['intensity']
        msg.timestamp.sec = int(time.time())
        msg.timestamp.nanosec = int((time.time() % 1) * 1e9)
        
        # Calculate elapsed time
        elapsed_sec = int(time.time() - rumination['last_update'])
        msg.elapsed_time.sec = elapsed_sec
        msg.elapsed_time.nanosec = 0
        
        # Query LLM to determine if this rumination should change emotional state
        self.query_llm_for_rumination(msg, rum_id)
        
        # Publish updated rumination
        self.rumination_pub.publish(msg)
    
    def consider_new_rumination(self):
        """Consider starting a new rumination based on current emotional state"""
        # Don't start new ruminations if at max capacity
        if len(self.active_ruminations) >= self.max_active_ruminations:
            return
            
        # Use emotion model to calculate overall intensity
        intensity = self.emotion_model.calculate_intensity(self.current_emotional_state)
        
        # Start rumination with probability based on emotional intensity
        if random.random() < intensity * 0.5:  # 50% chance at max intensity
            self.start_new_rumination()
    
    def start_new_rumination(self):
        """Start a new rumination"""
        # Create a new rumination ID
        rum_id = str(uuid.uuid4())
        
        # Use emotion model to determine the primary emotion
        primary_emotion = self.emotion_model.get_primary_emotion(self.current_emotional_state)
        
        # Create a rumination subject based on current primary emotion
        subject = f"Thinking about feeling {primary_emotion}"
        
        # Create initial rumination message
        msg = RuminationUpdate()
        msg.timestamp.sec = int(time.time())
        msg.timestamp.nanosec = int((time.time() % 1) * 1e9)
        msg.original_input_id = rum_id
        msg.rumination_stage = 0
        msg.elapsed_time.sec = 0
        msg.elapsed_time.nanosec = 0
        msg.intensity = self.emotion_model.calculate_intensity(self.current_emotional_state)
        msg.description = subject
        msg.is_final = False
        
        # Add to active ruminations
        self.active_ruminations[rum_id] = {
            'stage': 0,
            'intensity': msg.intensity,
            'subject': subject,
            'last_update': time.time(),
            'message': msg
        }
        
        # Publish the rumination
        self.rumination_pub.publish(msg)
        self.get_logger().info(f"ALAINA: Started new rumination {rum_id}: {subject}")
    
    def query_llm_for_rumination(self, rumination_msg, rum_id):
        """Query LLM to determine if and how this rumination should change emotional state"""
        # Build prompt for LLM
        prompt = self.build_rumination_prompt(rumination_msg)
        
        # Call LLM API (mocked for demo)
        response = self.call_llm_api(prompt)
        
        if response:
            # Parse response
            try:
                data = json.loads(response)
                should_update = data.get("should_change_state", False)
                
                # If LLM says to update emotional state
                if should_update:
                    # Create and publish emotional response
                    response = self.create_emotional_response(data, rum_id, rumination_msg)
                    self.emotional_response_pub.publish(response)
                    
                    # Update emotional state
                    self.update_emotional_state(data, rum_id)
            except json.JSONDecodeError:
                self.get_logger().error(f"ALAINA: Error parsing LLM response for rumination {rum_id}")
        else:
            self.get_logger().error(f"ALAINA: Failed to get LLM response for rumination {rum_id}")
    
    def build_rumination_prompt(self, rumination_msg):
        """Build a prompt for the LLM to determine how rumination affects emotional state."""
        # Get current emotional state dimensions using the emotion model
        dimensions = self.emotion_model.get_dimensions()
        dimensions_state = {}
        for dim in dimensions:
            dimensions_state[dim] = self.emotion_model.get_emotion_value(self.current_emotional_state, dim)
        
        # Get all basic emotions
        all_emotions = self.emotion_model.get_all_emotions()
        emotions_state = {}
        for emotion in all_emotions:
            emotions_state[emotion] = self.emotion_model.get_emotion_value(self.current_emotional_state, emotion)
        
        # Get primary emotion
        primary_emotion = self.emotion_model.get_primary_emotion(self.current_emotional_state)
        
        # Build the prompt
        prompt = f"""You are the rumination system for a robot with emotions.

CURRENT EMOTIONAL STATE:
Dimensions: {json.dumps(dimensions_state, indent=2)}
Emotions: {json.dumps(emotions_state, indent=2)}
Primary emotion: {primary_emotion}

CURRENT RUMINATION:
Original Input ID: {rumination_msg.original_input_id}
Description: {rumination_msg.description}
Stage: {rumination_msg.rumination_stage} of {self.stages}
Intensity: {rumination_msg.intensity}

Based on this rumination and the robot's current emotional state, determine if the rumination should change the robot's emotional state, and if so, how it should change.

IMPORTANT: You MUST use one of these exact emotion names: {", ".join(all_emotions)}

Respond ONLY with a valid JSON object in the following format:
{{
  "should_change_state": true/false,
  "pleasure_delta": float (-1.0 to 1.0),
  "arousal_delta": float (-1.0 to 1.0),
  "dominance_delta": float (-1.0 to 1.0),
  "primary_emotion": string (one of: {", ".join([f'"{e}"' for e in all_emotions])}),
  "intensity": float (0.0 to 1.0),
  "confidence": float (0.0 to 1.0),
  "explanation": string
}}
"""
        return prompt
    
    def call_llm_api(self, prompt):
        """Mock LLM API call for rumination (for demo purposes)"""
        try:
            # Simulate an LLM response based on the rumination
            # In production, this would be an actual API call
            
            # Determine if we should update based on content
            should_update = random.random() < 0.7  # 70% chance to update
            
            # For demo purposes, analyze the prompt content to determine mood direction
            if "happiness" in prompt or "excited" in prompt:
                # Generally positive emotion in rumination
                pleasure_delta = random.uniform(0.01, 0.1)
                arousal_delta = random.uniform(-0.05, 0.1)
            elif "sad" in prompt or "fear" in prompt or "anxious" in prompt:
                # Generally negative emotion in rumination
                pleasure_delta = random.uniform(-0.1, -0.01)
                arousal_delta = random.uniform(-0.1, 0.05)
            else:
                # Neutral or mixed emotions
                pleasure_delta = random.uniform(-0.05, 0.05)
                arousal_delta = random.uniform(-0.05, 0.05)
            
            # For dominance, random subtle shift
            dominance_delta = random.uniform(-0.05, 0.05)
            
            # Extract all available emotions from the prompt
            all_emotions = self.emotion_model.get_all_emotions()
            
            # Make sure we return a valid emotion name (using the most likely one based on prompt content)
            emotion_weights = {}
            for emotion in all_emotions:
                # Count occurrences of emotion name in prompt to determine weight
                emotion_weights[emotion] = prompt.lower().count(emotion.lower())
            
            # Default to highest weighted emotion, or happiness/sadness based on pleasure
            if any(emotion_weights.values()):
                current_emotion = max(emotion_weights.items(), key=lambda x: x[1])[0]
            else:
                current_emotion = "happiness" if pleasure_delta > 0 else "sadness"
            
            # Generate response
            response = {
                "should_change_state": should_update,
                "pleasure_delta": pleasure_delta,
                "arousal_delta": arousal_delta,
                "dominance_delta": dominance_delta,
                "primary_emotion": current_emotion,
                "intensity": random.uniform(0.3, 0.8),
                "confidence": random.uniform(0.7, 0.9),
                "explanation": f"Continued rumination about {current_emotion} is affecting emotional state."
            }
            
            return json.dumps(response)
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error in LLM call: {str(e)}")
            return None
    
    def create_emotional_response(self, data, rum_id, rumination_msg):
        """Create an emotional response from the rumination."""
        response = EmotionalResponse()
        response.stimulus_id = rum_id
        response.timestamp = self.get_clock().now().to_msg()
        response.is_rumination = True
        response.response_text = f"Rumination response: {data.get('explanation', 'No explanation')}"
        response.source = "rumination_engine"
        response.pleasure_delta = data.get("pleasure_delta", 0.0)
        response.arousal_delta = data.get("arousal_delta", 0.0)
        response.dominance_delta = data.get("dominance_delta", 0.0)
        response.primary_emotion = data.get("primary_emotion", "neutral")
        response.intensity = data.get("intensity", 0.5)
        response.confidence = data.get("confidence", 0.8)
        response.metadata = json.dumps({
            "source": "rumination_engine",
            "rumination_id": rum_id,
            "rumination_stage": rumination_msg.rumination_stage,
            "intensity": rumination_msg.intensity,
            "elapsed_time": rumination_msg.elapsed_time.sec + (rumination_msg.elapsed_time.nanosec / 1e9)
        })
        
        # Store copies of the emotional state
        response.previous_state = copy.deepcopy(self.current_emotional_state)
        
        # Create new state based on changes
        response.new_state = copy.deepcopy(self.current_emotional_state)
        # We'll update this after the actual state update
        
        return response
    
    def update_emotional_state(self, llm_data, rum_id):
        """Update emotional state using service call"""
        # Wait for service to be available
        while not self.emotion_modify_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ALAINA: Waiting for emotion_modify service...')
        
        # Create service request for pleasure
        pleasure_request = EmotionModify.Request()
        pleasure_request.modification_type = "relative"
        pleasure_request.specific_emotion = "pleasure"
        pleasure_request.value = llm_data.get("pleasure_delta", 0.0)
        pleasure_request.reason = f"Rumination: {rum_id}"
        pleasure_request.override_safety = False
        
        # Call service for pleasure
        pleasure_future = self.emotion_modify_client.call_async(pleasure_request)
        
        # Create service request for arousal
        arousal_request = EmotionModify.Request()
        arousal_request.modification_type = "relative"
        arousal_request.specific_emotion = "arousal"
        arousal_request.value = llm_data.get("arousal_delta", 0.0)
        arousal_request.reason = f"Rumination: {rum_id}"
        arousal_request.override_safety = False
        
        # Call service for arousal
        arousal_future = self.emotion_modify_client.call_async(arousal_request)
        
        # Create service request for dominance
        dominance_request = EmotionModify.Request()
        dominance_request.modification_type = "relative"
        dominance_request.specific_emotion = "dominance"
        dominance_request.value = llm_data.get("dominance_delta", 0.0)
        dominance_request.reason = f"Rumination: {rum_id}"
        dominance_request.override_safety = False
        
        # Call service for dominance
        dominance_future = self.emotion_modify_client.call_async(dominance_request)
        
        # Create service request for primary emotion
        emotion_request = EmotionModify.Request()
        emotion_request.modification_type = "specific"
        emotion_request.specific_emotion = llm_data.get("primary_emotion", "neutral")
        emotion_request.value = llm_data.get("intensity", 0.5)
        emotion_request.reason = f"Rumination: {rum_id}"
        emotion_request.override_safety = False
        
        # Call service for primary emotion
        emotion_future = self.emotion_modify_client.call_async(emotion_request)
        
        # Add callbacks
        pleasure_future.add_done_callback(lambda f: self.emotion_modify_callback(f, rum_id, "pleasure"))
        arousal_future.add_done_callback(lambda f: self.emotion_modify_callback(f, rum_id, "arousal"))
        dominance_future.add_done_callback(lambda f: self.emotion_modify_callback(f, rum_id, "dominance"))
        emotion_future.add_done_callback(lambda f: self.emotion_modify_callback(f, rum_id, "primary_emotion"))
    
    def emotion_modify_callback(self, future, rum_id, emotion_type):
        """Callback for emotion modify service response"""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f"ALAINA: Successfully modified {emotion_type} for rumination {rum_id}")
            else:
                self.get_logger().error(f"ALAINA: Failed to modify {emotion_type} for rumination {rum_id}: {response.error_message}")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Exception in emotion modify callback: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    rumination_engine = RuminationEngine()
    
    try:
        rclpy.spin(rumination_engine)
    except KeyboardInterrupt:
        pass
    finally:
        rumination_engine.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 