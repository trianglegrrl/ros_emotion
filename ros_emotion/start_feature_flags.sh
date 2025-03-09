#!/bin/bash

# This script starts the feature flags manager in the Docker container

# Source ROS environment
source /opt/ros/foxy/setup.bash
source /ros_ws/install/setup.bash

# Run the feature flags manager
exec ros2 run ros_emotion feature_flags_manager.py 