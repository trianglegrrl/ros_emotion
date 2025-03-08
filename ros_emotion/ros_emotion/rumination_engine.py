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
            'emotion_modify'
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
        self.get_logger().info(f"ALAINA: Received rumination update: {msg.rumination_id}")
        
        # If this is a new rumination, add it to active ruminations
        if msg.rumination_id not in self.active_ruminations:
            self.active_ruminations[msg.rumination_id] = {
                'stage': 0,
                'intensity': msg.intensity,
                'subject': msg.subject,
                'last_update': time.time(),
                'message': msg
            }
            self.get_logger().info(f"ALAINA: Added new rumination {msg.rumination_id}: {msg.subject}")
        else:
            # Update existing rumination
            self.active_ruminations[msg.rumination_id]['stage'] = msg.stage
            self.active_ruminations[msg.rumination_id]['intensity'] = msg.intensity
            self.active_ruminations[msg.rumination_id]['last_update'] = time.time()
            self.active_ruminations[msg.rumination_id]['message'] = msg
            self.get_logger().info(f"ALAINA: Updated rumination {msg.rumination_id} to stage {msg.stage}")
    
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
        msg.stage = rumination['stage']
        msg.intensity = rumination['intensity']
        msg.timestamp.sec = int(time.time())
        msg.timestamp.nanosec = int((time.time() % 1) * 1e9)
        
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
        
        # Create a rumination subject based on current primary emotion
        subject = f"Thinking about feeling {self.current_emotional_state.primary_emotion}"
        
        # Create initial rumination message
        msg = RuminationUpdate()
        msg.rumination_id = rum_id
        msg.timestamp.sec = int(time.time())
        msg.timestamp.nanosec = int((time.time() % 1) * 1e9)
        msg.stage = 0
        msg.intensity = self.current_emotional_state.intensity
        msg.subject = subject
        msg.content = f"Initial rumination on {self.current_emotional_state.primary_emotion}"
        msg.metadata = json.dumps({
            "pleasure": self.current_emotional_state.pleasure,
            "arousal": self.current_emotional_state.arousal,
            "dominance": self.current_emotional_state.dominance
        })
        
        # Add to active ruminations
        self.active_ruminations[rum_id] = {
            'stage': 0,
            'intensity': msg.intensity,
            'subject': subject,
            'last_update': time.time(),
            'message': msg
        }
        
        # Publish new rumination
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
        """Build prompt for LLM to analyze rumination"""
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
        prompt = f"""You are the rumination engine for a robot's emotional system.
Rumination is the process of repeatedly thinking about the same emotion or situation over time.

The robot is currently ruminating on:
Subject: {rumination_msg.subject}
Stage: {rumination_msg.stage} of {self.stages}
Intensity: {rumination_msg.intensity}
Content: {rumination_msg.content}

The robot's current emotional state is:
{json.dumps(current_state, indent=2)}

Based on this rumination at this stage, determine:
1. Should this rumination change the robot's emotional state?
2. If yes, how should the emotional state change?

Respond ONLY with a valid JSON object in the following format:
{
  "should_update": true or false,
  "pleasure_delta": float (-0.2 to 0.2),
  "arousal_delta": float (-0.2 to 0.2),
  "dominance_delta": float (-0.2 to 0.2),
  "primary_emotion": string,
  "intensity": float (0.0 to 1.0),
  "confidence": float (0.0 to 1.0),
  "response_text": string
}

Note: The changes should be subtle, as rumination typically has a gradual effect on emotions."""
        
        return prompt
    
    def call_llm_api(self, prompt):
        """Mock LLM API call for rumination (for demo purposes)"""
        try:
            # Simulate an LLM response based on the rumination
            # In production, this would be an actual API call
            
            # Determine if we should update based on content
            should_update = random.random() < 0.7  # 70% chance to update
            
            # For demo purposes, analyze the prompt content to determine mood direction
            if "joy" in prompt or "happiness" in prompt or "excited" in prompt:
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
            emotion_words = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "trust", "anticipation"]
            current_emotion = "neutral"
            for emotion in emotion_words:
                if emotion in prompt.lower():
                    current_emotion = emotion
                    break
            
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
    
    def create_emotional_response(self, llm_data, rum_id, rumination_msg):
        """Create and publish emotional response message"""
        response = EmotionalResponse()
        response.timestamp.sec = int(time.time())
        response.timestamp.nanosec = int((time.time() % 1) * 1e9)
        response.stimulus_id = rum_id
        response.is_rumination = True
        response.response_text = llm_data.get("response_text", "")
        response.source = "rumination"
        response.previous_state = self.current_emotional_state
        response.pleasure_delta = llm_data.get("pleasure_delta", 0.0)
        response.arousal_delta = llm_data.get("arousal_delta", 0.0)
        response.dominance_delta = llm_data.get("dominance_delta", 0.0)
        response.primary_emotion = llm_data.get("primary_emotion", "neutral")
        response.intensity = llm_data.get("intensity", 0.5)
        response.confidence = llm_data.get("confidence", 0.5)
        response.metadata = json.dumps({
            "rumination_stage": rumination_msg.stage,
            "rumination_subject": rumination_msg.subject
        })
        
        # Publish the response
        self.emotional_response_pub.publish(response)
        self.get_logger().info(f"ALAINA: Published emotional response for rumination {rum_id}")
    
    def update_emotional_state(self, llm_data, rum_id):
        """Update emotional state using service call"""
        # Wait for service to be available
        while not self.emotion_modify_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ALAINA: Waiting for emotion_modify service...')
        
        # Create service request
        request = EmotionModify.Request()
        request.pleasure_delta = llm_data.get("pleasure_delta", 0.0)
        request.arousal_delta = llm_data.get("arousal_delta", 0.0)
        request.dominance_delta = llm_data.get("dominance_delta", 0.0)
        request.primary_emotion = llm_data.get("primary_emotion", "neutral")
        request.intensity = llm_data.get("intensity", 0.5)
        
        # Call service
        future = self.emotion_modify_client.call_async(request)
        future.add_done_callback(lambda f: self.emotion_modify_callback(f, rum_id))
    
    def emotion_modify_callback(self, future, rum_id):
        """Callback for emotion modify service response"""
        try:
            response = future.result()
            self.get_logger().info(f"ALAINA: Emotional state updated successfully for rumination {rum_id}")
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