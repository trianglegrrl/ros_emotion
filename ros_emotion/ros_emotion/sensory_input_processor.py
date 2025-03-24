#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String

# Fix import of custom messages
try:
    from ros_emotion_msgs.msg import SensoryInput
except ImportError:
    # Fallback to local message definition
    from ros_emotion.msg import SensoryInput

import uuid
import json
from collections import deque
import ros_emotion.utils as utils
from dotenv import load_dotenv

class SensoryInputProcessor(Node):
    def __init__(self):
        super().__init__('sensory_input_processor')
        
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self.config = utils.load_config(self)
        self.processor_config = self.config.get('sensory_input_processor', {})
        
        # Create QoS profile
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create publishers
        self.sensory_input_pub = self.create_publisher(
            SensoryInput, 
            'sensory_input', 
            qos
        )
        
        # Create subscribers for different types of sensory inputs
        self.text_input_sub = self.create_subscription(
            String,
            'text_input',
            self.text_input_callback,
            qos
        )
        
        self.visual_input_sub = self.create_subscription(
            String,
            'visual_input',
            self.visual_input_callback,
            qos
        )
        
        self.auditory_input_sub = self.create_subscription(
            String,
            'auditory_input',
            self.auditory_input_callback,
            qos
        )
        
        self.touch_input_sub = self.create_subscription(
            String,
            'touch_input',
            self.touch_input_callback,
            qos
        )
        
        # Input processing queue
        self.input_queue = deque(maxlen=100)
        
        self.get_logger().info('ALAINA: Sensory input processor initialized')

    def process_input(self, input_type, description, raw_data=None, source=None, 
                     intensity=None, priority=None, confidence=1.0, metadata=None):
        """
        Process a sensory input and publish it to the sensory_input topic.
        
        Args:
            input_type (str): Type of input (e.g., 'text', 'visual', 'audio', 'touch')
            description (str): Human-readable description of the input
            raw_data (optional): Raw data associated with the input
            source (str, optional): Source of the input (e.g., 'user', 'environment')
            intensity (float, optional): Intensity of the input (0.0 to 1.0)
            priority (float, optional): Priority of the input (0.0 to 1.0)
            confidence (float, optional): Confidence in the input (0.0 to 1.0)
            metadata (dict, optional): Additional metadata as key-value pairs
        
        Returns:
            str: The generated input ID
        """
        # Generate a unique ID for this input
        input_id = str(uuid.uuid4())
        
        # Set default values if not provided
        if source is None:
            source = "unknown"
            
        if intensity is None:
            intensity = 0.5
            
        if priority is None:
            priority = 0.5
            
        if metadata is None:
            metadata = {}
            
        # Create the sensory input message
        msg = SensoryInput()
        msg.input_id = input_id
        msg.input_type = input_type
        msg.description = description
        msg.source = source
        msg.intensity = float(intensity)
        msg.priority = float(priority)
        msg.confidence = float(confidence)
        
        # Add raw data if provided
        if raw_data:
            if isinstance(raw_data, str):
                msg.raw_data = raw_data
            else:
                try:
                    msg.raw_data = json.dumps(raw_data)
                except:
                    self.get_logger().warn(f"ALAINA: Could not serialize raw_data to JSON for input {input_id}")
        
        # Add metadata if provided
        if metadata:
            try:
                msg.metadata = json.dumps(metadata)
            except:
                self.get_logger().warn(f"ALAINA: Could not serialize metadata to JSON for input {input_id}")
        
        # Publish the message
        self.sensory_input_pub.publish(msg)
        
        self.get_logger().info(f"ALAINA: Published sensory input [{input_id}]: {description}")
        
        return input_id

    def text_input_callback(self, msg):
        """Process text input."""
        text = msg.data.strip()
        
        if not text:
            return
            
        # Extract intensity and confidence through simple heuristics
        intensity = 0.5  # Default
        confidence = 1.0  # Default for direct text input
        
        # Uppercase text might indicate higher intensity
        if text.isupper():
            intensity = 0.8
            
        # Longer text might have higher impact
        if len(text) > 100:
            intensity = min(intensity + 0.2, 1.0)
            
        # Process the text input
        self.process_input(
            input_type='text',
            description=text,
            raw_data=text,
            source='user',
            intensity=intensity,
            confidence=confidence,
            metadata={
                'length': len(text),
                'uppercase_ratio': sum(1 for c in text if c.isupper()) / max(1, len(text))
            }
        )

    def visual_input_callback(self, msg):
        """Process visual input."""
        description = msg.data
        
        if not description:
            return
            
        # For visual input, we might have different confidence levels
        # depending on the vision system's capabilities
        confidence = 0.8  # Default for vision system
        
        # Process the visual input
        self.process_input(
            input_type='visual',
            description=description,
            source='environment',
            intensity=0.6,  # Visual inputs often have higher salience
            confidence=confidence,
            metadata={
                'visual_type': 'image_description',  # This could be more specific based on the vision system
                'processing_time': 'real_time'
            }
        )

    def auditory_input_callback(self, msg):
        """Process auditory input."""
        description = msg.data
        
        if not description:
            return
            
        # Auditory inputs might have different urgency levels
        intensity = 0.7  # Default for auditory, as sounds are often attention-grabbing
        
        # Process the auditory input
        self.process_input(
            input_type='auditory',
            description=description,
            source='environment',
            intensity=intensity,
            confidence=0.85,
            metadata={
                'audio_type': 'speech',  # Could be 'noise', 'music', etc.
                'volume': 'medium'  # Could have actual dB values
            }
        )

    def touch_input_callback(self, msg):
        """Process touch input."""
        description = msg.data
        
        if not description:
            return
            
        # Touch inputs are often high intensity and high confidence
        intensity = 0.8
        
        # Process the touch input
        self.process_input(
            input_type='touch',
            description=description,
            source='physical',
            intensity=intensity,
            confidence=0.95,
            metadata={
                'touch_type': 'contact',
                'pressure': 'medium',
                'location': 'unspecified'
            }
        )

def main(args=None):
    rclpy.init(args=args)
    node = SensoryInputProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 