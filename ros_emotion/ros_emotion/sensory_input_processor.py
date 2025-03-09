#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import SensoryInput
from std_msgs.msg import String
import uuid
import json
from collections import deque
import ros_emotion.utils as utils

class SensoryInputProcessor(Node):
    def __init__(self):
        super().__init__('sensory_input_processor')
        
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
        
        # Create a buffer for recent sensory inputs
        buffer_size = self.processor_config.get('buffer_size', 10)
        self.sensory_buffer = deque(maxlen=buffer_size)
        
        # Default priorities for different input types
        self.default_priorities = self.processor_config.get('default_priorities', {
            'visual': 0.7,
            'auditory': 0.8,
            'text': 0.5,
            'touch': 0.9,
            'combined': 0.8
        })
        
        self.get_logger().info("ALAINA: Sensory Input Processor initialized")
    
    def process_input(self, input_type, description, raw_data=None, source=None, 
                     intensity=None, priority=None, confidence=1.0, metadata=None):
        """Process a sensory input and publish it."""
        # Create a new sensory input message
        msg = SensoryInput()
        
        # Set timestamp
        msg.timestamp = utils.get_current_time()
        
        # Set input type
        msg.input_type = input_type
        
        # Set description
        msg.description = description
        
        # Set raw data if provided
        msg.raw_data = raw_data if raw_data is not None else ""
        
        # Set source
        msg.source = source if source is not None else "unknown"
        
        # Set intensity (default to 1.0 if not provided)
        msg.intensity = float(intensity) if intensity is not None else 1.0
        
        # Set priority (use default for input type if not provided)
        if priority is not None:
            msg.priority = float(priority)
        else:
            msg.priority = self.default_priorities.get(input_type, 0.5)
        
        # Set confidence
        msg.confidence = float(confidence)
        
        # Set metadata
        if metadata is not None:
            if isinstance(metadata, dict):
                msg.metadata = json.dumps(metadata)
            else:
                msg.metadata = str(metadata)
        else:
            msg.metadata = "{}"
        
        # Add to buffer
        self.sensory_buffer.append(msg)
        
        # Publish the sensory input
        self.sensory_input_pub.publish(msg)
        
        self.get_logger().info(f"ALAINA: Published {input_type} sensory input: {description}")
        
        return msg
    
    def text_input_callback(self, msg):
        """Process text input."""
        try:
            # Try to parse as JSON for structured input
            data = json.loads(msg.data)
            description = data.get('description', 'No description')
            source = data.get('source', 'text_input')
            intensity = data.get('intensity', 0.5)
            priority = data.get('priority', None)
            confidence = data.get('confidence', 1.0)
            metadata = data.get('metadata', {})
            
            self.process_input(
                input_type='text',
                description=description,
                raw_data=msg.data,
                source=source,
                intensity=intensity,
                priority=priority,
                confidence=confidence,
                metadata=metadata
            )
        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            self.process_input(
                input_type='text',
                description=msg.data,
                raw_data=msg.data,
                source='text_input'
            )
    
    def visual_input_callback(self, msg):
        """Process visual input."""
        try:
            # Try to parse as JSON for structured input
            data = json.loads(msg.data)
            description = data.get('description', 'No description')
            source = data.get('source', 'visual_input')
            intensity = data.get('intensity', 0.7)
            priority = data.get('priority', None)
            confidence = data.get('confidence', 1.0)
            metadata = data.get('metadata', {})
            
            self.process_input(
                input_type='visual',
                description=description,
                raw_data=msg.data,
                source=source,
                intensity=intensity,
                priority=priority,
                confidence=confidence,
                metadata=metadata
            )
        except json.JSONDecodeError:
            # If not JSON, treat as plain text description
            self.process_input(
                input_type='visual',
                description=msg.data,
                raw_data=msg.data,
                source='visual_input'
            )
    
    def auditory_input_callback(self, msg):
        """Process auditory input."""
        try:
            # Try to parse as JSON for structured input
            data = json.loads(msg.data)
            description = data.get('description', 'No description')
            source = data.get('source', 'auditory_input')
            intensity = data.get('intensity', 0.8)
            priority = data.get('priority', None)
            confidence = data.get('confidence', 1.0)
            metadata = data.get('metadata', {})
            
            self.process_input(
                input_type='auditory',
                description=description,
                raw_data=msg.data,
                source=source,
                intensity=intensity,
                priority=priority,
                confidence=confidence,
                metadata=metadata
            )
        except json.JSONDecodeError:
            # If not JSON, treat as plain text description
            self.process_input(
                input_type='auditory',
                description=msg.data,
                raw_data=msg.data,
                source='auditory_input'
            )
    
    def touch_input_callback(self, msg):
        """Process touch input."""
        try:
            # Try to parse as JSON for structured input
            data = json.loads(msg.data)
            description = data.get('description', 'No description')
            source = data.get('source', 'touch_input')
            intensity = data.get('intensity', 0.9)
            priority = data.get('priority', None)
            confidence = data.get('confidence', 1.0)
            metadata = data.get('metadata', {})
            
            self.process_input(
                input_type='touch',
                description=description,
                raw_data=msg.data,
                source=source,
                intensity=intensity,
                priority=priority,
                confidence=confidence,
                metadata=metadata
            )
        except json.JSONDecodeError:
            # If not JSON, treat as plain text description
            self.process_input(
                input_type='touch',
                description=msg.data,
                raw_data=msg.data,
                source='touch_input'
            )

def main(args=None):
    rclpy.init(args=args)
    node = SensoryInputProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("ALAINA: Keyboard interrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 