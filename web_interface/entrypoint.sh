#!/bin/bash
set -e

# Source ROS environment
source "/opt/ros/$ROS_DISTRO/setup.bash"

# Create workspace and build the ros_emotion package
mkdir -p /ros_ws/src || true
cd /ros_ws

# Check if the ros_emotion package is already in the workspace
if [ ! -d "/ros_ws/src/ros_emotion" ] && [ -d "/var/www/html/ros_emotion" ]; then
    echo "Copying ros_emotion package from mounted volume..."
    cp -r /var/www/html/ros_emotion /ros_ws/src/
fi

# Make Python scripts executable
find /ros_ws/src -name "*.py" -exec chmod +x {} \; 2>/dev/null || true

# Build the package
echo "Building ros_emotion package..."
colcon build --symlink-install --packages-select ros_emotion

# Source the workspace
source "/ros_ws/install/setup.bash"

# Start nginx
service nginx start

# Start rosbridge server
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

# Log the success
echo "ROS emotion package built and started successfully"
echo "Web interface available at http://localhost:9999"
echo "All log files can be found in: ~/.ros/log"

# Keep container running
exec "$@" 