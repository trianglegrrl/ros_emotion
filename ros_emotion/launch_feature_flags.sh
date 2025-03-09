#!/bin/bash

source /opt/ros/$ROS_DISTRO/setup.bash
source /ros_ws/install/setup.bash

# Start the feature flags manager and wait for it to initialize
ros2 run ros_emotion feature_flags_manager &
FEATURE_FLAGS_PID=$!

# Wait a moment for the service to initialize
echo "Starting feature flags manager..."
sleep 5

# Verify if it's running
if ps -p $FEATURE_FLAGS_PID > /dev/null; then
    echo "Feature flags manager started successfully."
else
    echo "Warning: Feature flags manager may not have started properly."
fi 