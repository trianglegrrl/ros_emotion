#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from ros_emotion.srv import FeatureFlags
import json
import os
import sys

class FeatureFlagsManager(Node):
    """Node to manage feature flags for the ROS Emotion system."""
    
    def __init__(self):
        super().__init__('feature_flags_manager')
        
        # Add startup logging
        self.get_logger().info("ALAINA: Feature Flags Manager node starting initialization")
        self.get_logger().info(f"ALAINA: Python executable: {sys.executable}")
        self.get_logger().info(f"ALAINA: Current working directory: {os.getcwd()}")
        
        # Create the service
        self.srv = self.create_service(
            FeatureFlags,
            'feature_flags',
            self.handle_feature_flags
        )
        
        # Initialize feature flags
        self.feature_flags = {}
        self.data_dir = os.path.join(os.path.expanduser('~'), '.ros_emotion')
        self.flags_file = os.path.join(self.data_dir, 'feature_flags.json')
        
        self.get_logger().info(f"ALAINA: Feature flags will be stored at: {self.flags_file}")
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir)
                self.get_logger().info(f"ALAINA: Created data directory: {self.data_dir}")
            except Exception as e:
                self.get_logger().error(f"ALAINA: Failed to create data directory: {e}")
        
        # Load existing flags
        self.load_feature_flags()
        
        # Set default flags if necessary
        self.initialize_default_flags()
        
        self.get_logger().info("ALAINA: Feature Flags Manager initialized successfully")
        self.get_logger().info(f"ALAINA: Active feature flags: {json.dumps(self.feature_flags, indent=2)}")
        
        # Periodically save feature flags to persist across restarts
        self.save_timer = self.create_timer(30.0, self.save_feature_flags)
    
    def initialize_default_flags(self):
        """Initialize default feature flags if they don't exist."""
        default_flags = {
            'rumination_enabled': {
                'value': True,
                'description': 'Enable/disable the rumination engine'
            },
            'llm_integration_enabled': {
                'value': True,
                'description': 'Enable/disable LLM integration for sensory processing'
            },
            'use_llm_for_rumination': {
                'value': False,
                'description': 'Enable/disable LLM calls during rumination process'
            },
            'personality_influence_enabled': {
                'value': True,
                'description': 'Enable/disable personality influence on emotional state'
            },
            'emotion_decay_enabled': {
                'value': True,
                'description': 'Enable/disable natural decay of emotions over time'
            }
        }
        
        # Only add flags that don't already exist
        for flag_name, flag_data in default_flags.items():
            if flag_name not in self.feature_flags:
                self.feature_flags[flag_name] = flag_data
                self.get_logger().info(f"ALAINA: Added default feature flag: {flag_name} = {flag_data['value']}")
                
    def load_feature_flags(self):
        """Load feature flags from file if it exists."""
        try:
            if os.path.exists(self.flags_file):
                with open(self.flags_file, 'r') as f:
                    saved_flags = json.load(f)
                    # Only update values for flags that exist in our default set
                    for flag_name, flag_data in saved_flags.items():
                        if flag_name in self.feature_flags:
                            self.feature_flags[flag_name]['value'] = flag_data.get('value', 
                                                                               self.feature_flags[flag_name]['value'])
                    self.get_logger().info("ALAINA: Loaded feature flags from file")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error loading feature flags: {str(e)}")
    
    def save_feature_flags(self):
        """Save current feature flags to file."""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.flags_file), exist_ok=True)
            
            with open(self.flags_file, 'w') as f:
                json.dump(self.feature_flags, f, indent=2)
            self.get_logger().debug("ALAINA: Saved feature flags to file")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error saving feature flags: {str(e)}")
    
    def handle_feature_flags(self, request, response):
        """Handle feature flags service requests."""
        response.success = True
        response.error_message = ""
        
        # Initialize response arrays
        response.feature_names = []
        response.feature_values = []
        response.feature_descriptions = []
        
        try:
            # List all feature flags
            if request.operation == "list":
                for flag_name, flag_data in self.feature_flags.items():
                    response.feature_names.append(flag_name)
                    response.feature_values.append(str(flag_data['value']).lower())
                    response.feature_descriptions.append(flag_data['description'])
            
            # Get a specific feature flag
            elif request.operation == "get":
                if request.feature_name in self.feature_flags:
                    flag_data = self.feature_flags[request.feature_name]
                    response.feature_names = [request.feature_name]
                    response.feature_values = [str(flag_data['value']).lower()]
                    response.feature_descriptions = [flag_data['description']]
                else:
                    response.success = False
                    response.error_message = f"Feature flag '{request.feature_name}' not found"
            
            # Set a feature flag value
            elif request.operation == "set":
                if request.feature_name in self.feature_flags:
                    # Convert string to boolean
                    new_value = request.value.lower() in ('true', 'yes', '1', 'y')
                    old_value = self.feature_flags[request.feature_name]['value']
                    
                    # Update value
                    self.feature_flags[request.feature_name]['value'] = new_value
                    
                    # Log the change
                    self.get_logger().info(f"ALAINA: Feature flag '{request.feature_name}' changed from {old_value} to {new_value}")
                    
                    # Save immediately on changes
                    self.save_feature_flags()
                    
                    # Return updated flag
                    response.feature_names = [request.feature_name]
                    response.feature_values = [str(new_value).lower()]
                    response.feature_descriptions = [self.feature_flags[request.feature_name]['description']]
                else:
                    response.success = False
                    response.error_message = f"Feature flag '{request.feature_name}' not found"
            
            # Invalid operation
            else:
                response.success = False
                response.error_message = f"Invalid operation: {request.operation}. Valid operations are: list, get, set"
        
        except Exception as e:
            response.success = False
            response.error_message = f"Error processing request: {str(e)}"
            self.get_logger().error(f"ALAINA: Error handling feature flags request: {str(e)}")
        
        return response
    
    def is_feature_enabled(self, feature_name):
        """Check if a feature is enabled."""
        if feature_name in self.feature_flags:
            return self.feature_flags[feature_name]['value']
        # Default to enabled if feature flag doesn't exist
        return True

def main(args=None):
    print("ALAINA DEBUG: Feature Flags Manager main() function starting")
    
    try:
        rclpy.init(args=args)
        print("ALAINA DEBUG: ROS2 initialized successfully")
        
        node = FeatureFlagsManager()
        print("ALAINA DEBUG: FeatureFlagsManager node created")
        
        print("ALAINA DEBUG: Starting ROS2 spin")
        rclpy.spin(node)
    except Exception as e:
        print(f"ALAINA DEBUG: Error in feature_flags_manager: {e}")
    finally:
        # Save feature flags before shutting down
        if 'node' in locals():
            node.save_feature_flags()
            node.get_logger().info("ALAINA: Feature Flags Manager shutting down")
            node.destroy_node()
        rclpy.shutdown()
        print("ALAINA DEBUG: Feature Flags Manager shut down")

if __name__ == '__main__':
    main() 