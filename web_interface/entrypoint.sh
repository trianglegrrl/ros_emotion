#!/bin/bash
set -e

# Source ROS environment
source "/opt/ros/$ROS_DISTRO/setup.bash"

# Create workspace and build the ros_emotion package
mkdir -p /ros_ws/src || true
cd /ros_ws

# Build the package if it's not built yet
if [ ! -f "/ros_ws/install/setup.bash" ]; then
    echo "Building ros_emotion package..."
    colcon build --symlink-install --packages-select ros_emotion
else
    echo "ros_emotion package already built"
fi

# Source the workspace
source "/ros_ws/install/setup.bash"

# Start nginx
service nginx start

# Start rosbridge server
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

# Keep container running
exec "$@" 