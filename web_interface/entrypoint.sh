#!/bin/bash
set -e

# Source ROS environment
source "/opt/ros/$ROS_DISTRO/setup.bash"

# Start nginx
service nginx start

# Start rosbridge server
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

# Keep container running
exec "$@" 