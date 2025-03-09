from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'ros_emotion'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='ROS Emotion package for robot emotion processing system',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'publisher_node = ros_emotion.publisher_node:main',
            'emotional_state_manager = ros_emotion.emotional_state_manager:main',
            'sensory_input_processor = ros_emotion.sensory_input_processor:main',
            'llm_integration = ros_emotion.llm_integration:main',
            'rumination_engine = ros_emotion.rumination_engine:main',
            'visualization_node = ros_emotion.visualization_node:main',
            'test_input_publisher = ros_emotion.test_input_publisher:main',
        ],
    },
) 