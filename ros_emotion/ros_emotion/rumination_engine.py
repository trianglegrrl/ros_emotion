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

class RuminationEngine(Node):
    def __init__(self):
        super().__init__('rumination_engine')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.rumination_config = self.config.get('rumination_engine', {})
        
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
        """Handle a rumination update"""
        # Use original_input_id as the rumination ID
        rumination_id = msg.original_input_id
        self.get_logger().info(f"ALAINA: Received rumination update: {rumination_id}")
        
        # If this is a new rumination, add it to active ruminations
        if rumination_id not in self.active_ruminations:
            self.active_ruminations[rumination_id] = {
                'stage': 0,
                'intensity': msg.intensity,
                'subject': msg.description,
                'last_update': time.time(),
                'message': msg
            }
            self.get_logger().info(f"ALAINA: Added new rumination {rumination_id}: {msg.description}")
        else:
            # Update existing rumination
            self.active_ruminations[rumination_id]['stage'] = msg.rumination_stage
            self.active_ruminations[rumination_id]['intensity'] = msg.intensity
            self.active_ruminations[rumination_id]['last_update'] = time.time()
            self.active_ruminations[rumination_id]['message'] = msg
            self.get_logger().info(f"ALAINA: Updated rumination {rumination_id} to stage {msg.rumination_stage}")
    
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
            
        # Start rumination with probability based on emotional intensity
        intensity = self.current_emotional_state.intensity
        if random.random() < intensity * 0.5:  # 50% chance at max intensity
            self.start_new_rumination()
    
    def start_new_rumination(self):
        """Start a new rumination"""
        # Create a new rumination ID
        rum_id = str(uuid.uuid4())
        
        # Determine the primary emotion based on the highest value
        emotions = {
            "happiness": self.current_emotional_state.happiness,
            "sadness": self.current_emotional_state.sadness,
            "anger": self.current_emotional_state.anger,
            "fear": self.current_emotional_state.fear,
            "disgust": self.current_emotional_state.disgust,
            "surprise": self.current_emotional_state.surprise
        }
        primary_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        
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
        msg.intensity = self.current_emotional_state.intensity
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
                should_update = data.get("should_update", False)
                
                # If LLM says to update emotional state
                if should_update:
                    # Create and publish emotional response
                    self.create_emotional_response(data, rum_id, rumination_msg)
                    
                    # Update emotional state
                    self.update_emotional_state(data, rum_id)
            except json.JSONDecodeError:
                self.get_logger().error(f"ALAINA: Error parsing LLM response for rumination {rum_id}")
        else:
            self.get_logger().error(f"ALAINA: Failed to get LLM response for rumination {rum_id}")
    
    def build_rumination_prompt(self, rumination_msg):
        """Build a prompt for the LLM to determine how rumination affects emotional state."""
        # Get current emotional state
        current_state = {
            "pleasure": self.current_emotional_state.pleasure,
            "arousal": self.current_emotional_state.arousal,
            "dominance": self.current_emotional_state.dominance,
            "happiness": self.current_emotional_state.happiness,
            "sadness": self.current_emotional_state.sadness,
            "anger": self.current_emotional_state.anger,
            "fear": self.current_emotional_state.fear,
            "disgust": self.current_emotional_state.disgust,
            "surprise": self.current_emotional_state.surprise
        }
        emotions = {
            "happiness": self.current_emotional_state.happiness,
            "sadness": self.current_emotional_state.sadness,
            "anger": self.current_emotional_state.anger,
            "fear": self.current_emotional_state.fear,
            "disgust": self.current_emotional_state.disgust,
            "surprise": self.current_emotional_state.surprise
        }
        primary_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        
        # Build the prompt
        prompt = f"""You are the rumination system for a robot with emotions.

CURRENT EMOTIONAL STATE:
{json.dumps(current_state, indent=2)}
Primary emotion: {primary_emotion}

CURRENT RUMINATION:
Original Input ID: {rumination_msg.original_input_id}
Description: {rumination_msg.description}
Stage: {rumination_msg.rumination_stage} of {self.stages}
Intensity: {rumination_msg.intensity}

Based on this rumination and the robot's current emotional state, determine if the rumination should change the robot's emotional state, and if so, how it should change.

IMPORTANT: You MUST use one of these exact emotion names: happiness, sadness, anger, fear, disgust, surprise

Respond ONLY with a valid JSON object in the following format:
{{
  "should_change_state": true/false,
  "pleasure_delta": float (-1.0 to 1.0),
  "arousal_delta": float (-1.0 to 1.0),
  "dominance_delta": float (-1.0 to 1.0),
  "primary_emotion": string (one of: "happiness", "sadness", "anger", "fear", "disgust", "surprise"),
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
            
            # Extract current primary emotion from prompt
            emotion_words = ["happiness", "sadness", "anger", "fear", "disgust", "surprise"]
            current_emotion = "neutral"
            for emotion in emotion_words:
                if emotion in prompt.lower():
                    current_emotion = emotion
                    break
            
            # Make sure we return a valid emotion name
            if current_emotion == "neutral" or current_emotion not in emotion_words:
                # Default to happiness or sadness based on pleasure
                current_emotion = "happiness" if pleasure_delta > 0 else "sadness"
            
            # Realistic response text for rumination
            response_texts = [
                f"Continuing to think about feeling {current_emotion}...",
                f"The feeling of {current_emotion} is lingering...",
                f"Dwelling on the {current_emotion} feelings...",
                f"The {current_emotion} emotion continues to be processed...",
                f"Still processing these {current_emotion} feelings..."
            ]
            
            response = {
                "should_update": should_update,
                "pleasure_delta": pleasure_delta if should_update else 0.0,
                "arousal_delta": arousal_delta if should_update else 0.0,
                "dominance_delta": dominance_delta if should_update else 0.0,
                "primary_emotion": current_emotion,
                "intensity": random.uniform(0.2, 0.8),
                "confidence": random.uniform(0.6, 0.9),
                "response_text": random.choice(response_texts)
            }
            
            return json.dumps(response)
            
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error in LLM API call: {str(e)}")
            return None
    
    def create_emotional_response(self, data, rum_id, rumination_msg):
        """Create an emotional response from the rumination."""
        response = EmotionalResponse()
        response.stimulus_id = rum_id
        response.timestamp = self.get_clock().now().to_msg()
        response.is_rumination = True
        response.response_text = f"Rumination response: {data.get('description', 'No description')}"
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
                self.get_logger().info(f"ALAINA: Emotional state ({emotion_type}) updated successfully for rumination {rum_id}")
            else:
                self.get_logger().error(f"ALAINA: Failed to update emotional state ({emotion_type}) for rumination {rum_id}: {response.error_message}")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Service call failed: {str(e)}")

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