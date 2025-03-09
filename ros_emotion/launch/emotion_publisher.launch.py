from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros_emotion',
            executable='emotional_state_manager',
            name='emotional_state_manager',
            output='screen'
        ),
        Node(
            package='ros_emotion',
            executable='sensory_input_processor',
            name='sensory_input_processor',
            output='screen'
        ),
        Node(
            package='ros_emotion',
            executable='llm_integration',
            name='llm_integration',
            output='screen'
        ),
        Node(
            package='ros_emotion',
            executable='rumination_engine',
            name='rumination_engine',
            output='screen'
        ),
        Node(
            package='ros_emotion',
            executable='visualization_node',
            name='visualization_node',
            output='screen'
        )
    ]) 