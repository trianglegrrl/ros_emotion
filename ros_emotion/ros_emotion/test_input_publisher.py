#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import time
import random

class TestInputPublisher(Node):
    def __init__(self):
        super().__init__('test_input_publisher')
        
        # Create publishers for different input types
        self.text_pub = self.create_publisher(String, 'text_input', 10)
        self.visual_pub = self.create_publisher(String, 'visual_input', 10)
        self.auditory_pub = self.create_publisher(String, 'auditory_input', 10)
        self.touch_pub = self.create_publisher(String, 'touch_input', 10)
        
        # Create timer for publishing test inputs
        self.timer = self.create_timer(5.0, self.publish_test_input)
        
        # Sample inputs for testing
        self.text_inputs = [
            "The robot receives a compliment from a user",
            "A user criticizes the robot's performance",
            "The robot is told it did a good job",
            "Someone expresses disappointment in the robot",
            "A user thanks the robot for its help"
        ]
        
        self.visual_inputs = [
            "The robot sees a person smiling",
            "The robot observes someone crying",
            "The robot notices a person with an angry expression",
            "The robot sees a child playing happily",
            "The robot observes a tense interaction between people"
        ]
        
        self.auditory_inputs = [
            "The robot hears laughter",
            "The robot hears someone shouting angrily",
            "The robot hears soft, calm music",
            "The robot hears a loud, unexpected noise",
            "The robot hears someone crying"
        ]
        
        self.touch_inputs = [
            "The robot receives a gentle pat on its head",
            "The robot is pushed roughly",
            "The robot is hugged by a child",
            "The robot's arm is grabbed suddenly",
            "The robot is tapped lightly on the shoulder"
        ]
        
        self.get_logger().info("ALAINA: Test Input Publisher initialized")
    
    def publish_test_input(self):
        """Publish a random test input."""
        # Choose a random input type
        input_type = random.choice(['text', 'visual', 'auditory', 'touch'])
        
        if input_type == 'text':
            self.publish_text_input()
        elif input_type == 'visual':
            self.publish_visual_input()
        elif input_type == 'auditory':
            self.publish_auditory_input()
        elif input_type == 'touch':
            self.publish_touch_input()
    
    def publish_text_input(self):
        """Publish a text input."""
        msg = String()
        description = random.choice(self.text_inputs)
        
        # Create a structured JSON message
        data = {
            'description': description,
            'source': 'test_publisher',
            'intensity': random.uniform(0.3, 1.0),
            'confidence': random.uniform(0.7, 1.0)
        }
        
        msg.data = json.dumps(data)
        self.text_pub.publish(msg)
        self.get_logger().info(f"ALAINA: Published text input: {description}")
    
    def publish_visual_input(self):
        """Publish a visual input."""
        msg = String()
        description = random.choice(self.visual_inputs)
        
        # Create a structured JSON message
        data = {
            'description': description,
            'source': 'test_publisher',
            'intensity': random.uniform(0.3, 1.0),
            'confidence': random.uniform(0.7, 1.0)
        }
        
        msg.data = json.dumps(data)
        self.visual_pub.publish(msg)
        self.get_logger().info(f"ALAINA: Published visual input: {description}")
    
    def publish_auditory_input(self):
        """Publish an auditory input."""
        msg = String()
        description = random.choice(self.auditory_inputs)
        
        # Create a structured JSON message
        data = {
            'description': description,
            'source': 'test_publisher',
            'intensity': random.uniform(0.3, 1.0),
            'confidence': random.uniform(0.7, 1.0)
        }
        
        msg.data = json.dumps(data)
        self.auditory_pub.publish(msg)
        self.get_logger().info(f"ALAINA: Published auditory input: {description}")
    
    def publish_touch_input(self):
        """Publish a touch input."""
        msg = String()
        description = random.choice(self.touch_inputs)
        
        # Create a structured JSON message
        data = {
            'description': description,
            'source': 'test_publisher',
            'intensity': random.uniform(0.3, 1.0),
            'confidence': random.uniform(0.7, 1.0)
        }
        
        msg.data = json.dumps(data)
        self.touch_pub.publish(msg)
        self.get_logger().info(f"ALAINA: Published touch input: {description}")

def main(args=None):
    rclpy.init(args=args)
    node = TestInputPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("ALAINA: Keyboard interrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 