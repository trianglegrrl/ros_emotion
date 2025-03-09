#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import EmotionalState, RuminationUpdate
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA
from geometry_msgs.msg import Point, Vector3
import math
import numpy as np
from collections import deque
import ros_emotion.utils as utils
from ros_emotion.emotion_model import create_emotion_model

class VisualizationNode(Node):
    def __init__(self):
        super().__init__('visualization_node')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.viz_config = self.config.get('visualization', {})
        
        # Initialize the emotion model
        emotion_model_type = self.config.get('emotional_state_manager', {}).get('emotion_model_type', 'pad_basic')
        self.emotion_model = create_emotion_model(emotion_model_type)
        
        # Create QoS profile
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create publishers
        self.marker_pub = self.create_publisher(
            MarkerArray, 
            'emotion_visualization', 
            qos
        )
        
        # Create subscribers
        self.emotional_state_sub = self.create_subscription(
            EmotionalState,
            'emotional_state',
            self.emotional_state_callback,
            qos
        )
        
        self.rumination_sub = self.create_subscription(
            RuminationUpdate,
            'rumination_update',
            self.rumination_callback,
            qos
        )
        
        # Store the current emotional state
        self.current_emotional_state = None
        
        # Store active ruminations
        self.active_ruminations = {}
        
        # Store history for time series visualization
        history_length = self.viz_config.get('history_length', 100)
        self.pleasure_history = deque(maxlen=history_length)
        self.arousal_history = deque(maxlen=history_length)
        self.dominance_history = deque(maxlen=history_length)
        
        # Create timer for visualization updates
        update_frequency = self.viz_config.get('update_frequency', 10.0)
        self.update_timer = self.create_timer(
            1.0 / update_frequency,
            self.update_visualization
        )
        
        self.get_logger().info("ALAINA: Visualization Node initialized")
    
    def emotional_state_callback(self, msg):
        """Store the current emotional state."""
        self.current_emotional_state = msg
        
        # Add to history
        self.pleasure_history.append(msg.pleasure)
        self.arousal_history.append(msg.arousal)
        self.dominance_history.append(msg.dominance)
        
        self.get_logger().debug(f"ALAINA: Updated emotional state for visualization: {msg.description}")
    
    def rumination_callback(self, msg):
        """Track active ruminations."""
        if msg.is_final:
            # Remove from active ruminations
            if msg.original_input_id in self.active_ruminations:
                self.active_ruminations.pop(msg.original_input_id)
        else:
            # Add or update in active ruminations
            self.active_ruminations[msg.original_input_id] = msg
    
    def update_visualization(self):
        """Update the visualization markers."""
        if not self.current_emotional_state:
            return
        
        # Create a marker array for all visualizations
        marker_array = MarkerArray()
        
        # Add PAD model visualization (3D cube)
        pad_marker = self.create_pad_marker()
        marker_array.markers.append(pad_marker)
        
        # Add basic emotions visualization (bar chart)
        emotion_markers = self.create_emotion_markers()
        marker_array.markers.extend(emotion_markers)
        
        # Add rumination visualizations
        rumination_markers = self.create_rumination_markers()
        marker_array.markers.extend(rumination_markers)
        
        # Add history visualization (line graph)
        history_markers = self.create_history_markers()
        marker_array.markers.extend(history_markers)
        
        # Publish all markers
        self.marker_pub.publish(marker_array)
    
    def create_pad_marker(self):
        """Create a marker for the PAD model visualization."""
        marker = Marker()
        marker.header.frame_id = "emotion_frame"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "pad_model"
        marker.id = 0
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        
        # Position based on PAD values
        marker.pose.position.x = self.current_emotional_state.pleasure
        marker.pose.position.y = self.current_emotional_state.arousal
        marker.pose.position.z = self.current_emotional_state.dominance
        
        # Orientation (identity quaternion)
        marker.pose.orientation.w = 1.0
        
        # Size based on intensity
        size = 0.1 + self.current_emotional_state.intensity * 0.2
        marker.scale.x = size
        marker.scale.y = size
        marker.scale.z = size
        
        # Color based on emotions
        marker.color = self.get_emotion_color()
        
        # Don't auto-delete
        marker.lifetime.sec = 0
        
        return marker
    
    def create_emotion_markers(self):
        """Create markers for the basic emotions visualization."""
        markers = []
        
        # Get the emotions from the emotion model
        emotions = self.emotion_model.get_all_emotions()
        emotion_values = [(emotion, self.emotion_model.get_emotion_value(self.current_emotional_state, emotion)) 
                          for emotion in emotions]
        
        # Create a bar for each emotion
        for i, (emotion, value) in enumerate(emotion_values):
            marker = Marker()
            marker.header.frame_id = "emotion_frame"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "basic_emotions"
            marker.id = i
            marker.type = Marker.CUBE
            marker.action = Marker.ADD
            
            # Position (horizontal bar chart)
            marker.pose.position.x = 2.0  # Offset from PAD model
            marker.pose.position.y = i * 0.3 - 0.75  # Vertical position
            marker.pose.position.z = 0.0
            
            # Orientation (identity quaternion)
            marker.pose.orientation.w = 1.0
            
            # Size (width based on value)
            marker.scale.x = value * 0.5  # Width
            marker.scale.y = 0.2  # Height
            marker.scale.z = 0.1  # Depth
            
            # Color based on emotion using the emotion model
            marker.color = self.get_emotion_specific_color(emotion)
            
            # Don't auto-delete
            marker.lifetime.sec = 0
            
            markers.append(marker)
            
            # Add text label
            text_marker = Marker()
            text_marker.header.frame_id = "emotion_frame"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "basic_emotions_text"
            text_marker.id = i
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            # Position (next to bar)
            text_marker.pose.position.x = 2.0 + value * 0.5 + 0.1  # Just after the bar
            text_marker.pose.position.y = i * 0.3 - 0.75  # Same vertical position as bar
            text_marker.pose.position.z = 0.0
            
            # Orientation (identity quaternion)
            text_marker.pose.orientation.w = 1.0
            
            # Size (text height)
            text_marker.scale.z = 0.1  # Text height
            
            # Color (same as bar)
            text_marker.color = self.get_emotion_specific_color(emotion)
            
            # Text (emotion name and value)
            text_marker.text = f"{emotion}: {value:.2f}"
            
            # Don't auto-delete
            text_marker.lifetime.sec = 0
            
            markers.append(text_marker)
        
        return markers
    
    def create_rumination_markers(self):
        """Create markers for active ruminations."""
        markers = []
        
        for i, (rumination_id, rumination) in enumerate(self.active_ruminations.items()):
            marker = Marker()
            marker.header.frame_id = "emotion_frame"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "ruminations"
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            
            # Position (around the PAD point)
            angle = i * (2 * math.pi / max(1, len(self.active_ruminations)))
            radius = 0.3
            marker.pose.position.x = self.current_emotional_state.pleasure + radius * math.cos(angle)
            marker.pose.position.y = self.current_emotional_state.arousal + radius * math.sin(angle)
            marker.pose.position.z = self.current_emotional_state.dominance
            
            # Orientation (identity quaternion)
            marker.pose.orientation.w = 1.0
            
            # Size based on intensity
            size = 0.05 + rumination.intensity * 0.1
            marker.scale.x = size
            marker.scale.y = size
            marker.scale.z = size
            
            # Color (pulsing based on stage)
            alpha = 0.5 + 0.5 * math.sin(rumination.rumination_stage * 0.5)
            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 1.0
            marker.color.a = alpha
            
            # Don't auto-delete
            marker.lifetime.sec = 0
            
            markers.append(marker)
            
            # Add text label
            text_marker = Marker()
            text_marker.header.frame_id = "emotion_frame"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "rumination_labels"
            text_marker.id = i
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            # Position (above the sphere)
            text_marker.pose.position.x = marker.pose.position.x
            text_marker.pose.position.y = marker.pose.position.y
            text_marker.pose.position.z = marker.pose.position.z + 0.1
            
            # Orientation (identity quaternion)
            text_marker.pose.orientation.w = 1.0
            
            # Size (text height)
            text_marker.scale.z = 0.05  # Text height
            
            # Color (white)
            text_marker.color.r = 1.0
            text_marker.color.g = 1.0
            text_marker.color.b = 1.0
            text_marker.color.a = 1.0
            
            # Text
            text_marker.text = f"Stage {rumination.rumination_stage}"
            
            # Don't auto-delete
            text_marker.lifetime.sec = 0
            
            markers.append(text_marker)
        
        return markers
    
    def create_history_markers(self):
        """Create markers for the emotion history visualization."""
        markers = []
        
        if not self.pleasure_history:
            return markers
        
        # Create line strips for each dimension
        dimensions = [
            ("pleasure", self.pleasure_history, ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)),
            ("arousal", self.arousal_history, ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0)),
            ("dominance", self.dominance_history, ColorRGBA(r=0.0, g=0.0, b=1.0, a=1.0))
        ]
        
        for i, (name, history, color) in enumerate(dimensions):
            marker = Marker()
            marker.header.frame_id = "emotion_frame"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "emotion_history"
            marker.id = i
            marker.type = Marker.LINE_STRIP
            marker.action = Marker.ADD
            
            # Points for the line strip
            for j, value in enumerate(history):
                point = Point()
                point.x = -2.0 + j * 0.02  # X position (time)
                point.y = value  # Y position (value)
                point.z = i * 0.2 - 0.2  # Z position (separate dimensions)
                marker.points.append(point)
            
            # Line width
            marker.scale.x = 0.02  # Line width
            
            # Color
            marker.color = color
            
            # Don't auto-delete
            marker.lifetime.sec = 0
            
            markers.append(marker)
            
            # Add text label
            text_marker = Marker()
            text_marker.header.frame_id = "emotion_frame"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "history_labels"
            text_marker.id = i
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            # Position (at the start of the line)
            text_marker.pose.position.x = -2.0
            text_marker.pose.position.y = 0.0
            text_marker.pose.position.z = i * 0.2 - 0.2
            
            # Orientation (identity quaternion)
            text_marker.pose.orientation.w = 1.0
            
            # Size (text height)
            text_marker.scale.z = 0.1  # Text height
            
            # Color (same as line)
            text_marker.color = color
            
            # Text
            text_marker.text = name
            
            # Don't auto-delete
            text_marker.lifetime.sec = 0
            
            markers.append(text_marker)
        
        return markers
    
    def get_emotion_color(self):
        """Get a color representing the current emotional state."""
        color = ColorRGBA()
        
        # Red component based on pleasure (negative = more red)
        color.r = 0.5 - self.current_emotional_state.pleasure * 0.5
        
        # Green component based on arousal (positive = more green)
        color.g = 0.5 + self.current_emotional_state.arousal * 0.5
        
        # Blue component based on dominance (positive = more blue)
        color.b = 0.5 + self.current_emotional_state.dominance * 0.5
        
        # Alpha based on intensity
        color.a = 0.5 + self.current_emotional_state.intensity * 0.5
        
        return color
    
    def get_emotion_specific_color(self, emotion):
        """Get a color for a specific emotion using the emotion model."""
        # Get the color from the emotion model
        model_color = self.emotion_model.get_emotion_color(emotion)
        
        # Convert to ColorRGBA
        color = ColorRGBA()
        color.a = 1.0
        color.r = model_color[0]
        color.g = model_color[1]
        color.b = model_color[2]
        
        return color

def main(args=None):
    rclpy.init(args=args)
    node = VisualizationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("ALAINA: Keyboard interrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 