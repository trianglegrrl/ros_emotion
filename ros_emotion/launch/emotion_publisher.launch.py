from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros_emotion',
            executable='publisher_node.py',
            name='emotion_publisher',
            output='screen'
        )
    ]) 