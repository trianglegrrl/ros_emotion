#!/bin/bash

echo "Rebuilding ROS Emotion package with messages..."

# Source ROS
source /opt/ros/foxy/setup.bash

# Go to the ROS workspace
cd /ros_ws

# Clean build directories if they exist
rm -rf build/ros_emotion install/ros_emotion log/

# Rebuild the package
colcon build --packages-select ros_emotion

# Source the newly built package
source install/setup.bash

echo "Build complete. Testing imports..."

# Test imports
python3 -c "
import sys
try:
    from ros_emotion.msg import EmotionalState, SensoryInput, RuminationUpdate, EmotionalResponse
    print('✅ Successfully imported message types from ros_emotion.msg')
except ImportError as e:
    print('❌ Error importing message types:', e)
    sys.exit(1)

try:
    from ros_emotion.utils.config_loader import load_config
    print('✅ Successfully imported load_config from utils.config_loader')
except ImportError as e:
    print('❌ Error importing config_loader:', e)
    sys.exit(1)
"

echo "If no errors appeared above, the build was successful."
echo "You can now run your ROS nodes." 