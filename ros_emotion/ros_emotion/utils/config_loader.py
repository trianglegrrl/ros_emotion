#!/usr/bin/env python3

import yaml
import os
import ament_index_python.packages

def load_config(node, config_file='emotion_config.yaml'):
    """Load configuration from a YAML file."""
    try:
        # Try to find the package share directory
        package_name = 'ros_emotion'
        try:
            package_share_directory = ament_index_python.packages.get_package_share_directory(package_name)
            config_path = os.path.join(package_share_directory, 'config', config_file)
        except Exception:
            # Fallback to local directory
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', config_file)
        
        # If file doesn't exist, try another location
        if not os.path.exists(config_path):
            config_path = os.path.join('/ros_ws/src/ros_emotion/config', config_file)
        
        # If file still doesn't exist, use default values
        if not os.path.exists(config_path):
            node.get_logger().warning(f"ALAINA: Config file not found at {config_path}, using default values")
            return {}
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        node.get_logger().info(f"ALAINA: Loaded configuration from {config_path}")
        return config
    except Exception as e:
        node.get_logger().error(f"ALAINA: Failed to load configuration: {str(e)}")
        return {} 