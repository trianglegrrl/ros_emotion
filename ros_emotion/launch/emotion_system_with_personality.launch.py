#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, EnvironmentVariable

def generate_launch_description():
    """Generate launch description for the emotion system with personality model"""
    
    # Define launch arguments
    config_path_arg = DeclareLaunchArgument(
        'config_path',
        default_value='src/ros_emotion/config/emotion_config.yaml',
        description='Path to the configuration file'
    )
    
    personality_type_arg = DeclareLaunchArgument(
        'personality_type',
        default_value='hybrid',
        description='Type of personality model to use'
    )
    
    use_test_inputs_arg = DeclareLaunchArgument(
        'use_test_inputs',
        default_value='True',
        description='Whether to run the test input publisher'
    )
    
    # Get the configurations
    config_path = LaunchConfiguration('config_path')
    personality_type = LaunchConfiguration('personality_type')
    use_test_inputs = LaunchConfiguration('use_test_inputs')
    
    # Create the environment variables for the nodes
    env_vars = {
        'ROS_EMOTION_CONFIG_PATH': config_path,
        'PERSONALITY_MODEL_TYPE': personality_type
    }
    
    # Create the node descriptions
    nodes = [
        # Node Lifecycle Manager
        Node(
            package='ros_emotion',
            executable='node_lifecycle_manager.py',
            name='node_lifecycle_manager',
            output='screen',
            env=env_vars
        ),
        
        # Emotional State Manager
        Node(
            package='ros_emotion',
            executable='emotional_state_manager.py',
            name='emotional_state_manager',
            output='screen',
            env=env_vars,
            parameters=[{'personality_model_type': personality_type}]
        ),
        
        # LLM Integration
        Node(
            package='ros_emotion',
            executable='llm_integration.py',
            name='llm_integration',
            output='screen',
            env=env_vars,
            parameters=[{'personality_model_type': personality_type}]
        ),
        
        # Rumination Engine
        Node(
            package='ros_emotion',
            executable='rumination_engine.py',
            name='rumination_engine',
            output='screen',
            env=env_vars,
            parameters=[{'personality_model_type': personality_type}]
        ),
        
        # Sensory Input Processor
        Node(
            package='ros_emotion',
            executable='sensory_input_processor.py',
            name='sensory_input_processor',
            output='screen',
            env=env_vars
        ),
        
        # Visualization Node
        Node(
            package='ros_emotion',
            executable='visualization_node.py',
            name='visualization_node',
            output='screen',
            env=env_vars
        ),
    ]
    
    # Conditionally add the test input publisher
    test_input_node = Node(
        package='ros_emotion',
        executable='test_input_publisher.py',
        name='test_input_publisher',
        output='screen',
        env=env_vars,
        condition=LaunchConfiguration('use_test_inputs')
    )
    
    # Create the launch description
    ld = LaunchDescription([
        config_path_arg,
        personality_type_arg,
        use_test_inputs_arg
    ])
    
    # Add all nodes to the launch description
    for node in nodes:
        ld.add_action(node)
    
    # Add test input node if enabled
    ld.add_action(test_input_node)
    
    return ld 