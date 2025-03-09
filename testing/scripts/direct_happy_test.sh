#!/bin/bash

# Determine the script location and set up paths
SCRIPT_DIR=$(dirname "$0")
TESTING_DIR=$(dirname "$SCRIPT_DIR")
RESULTS_DIR="$TESTING_DIR/results"

echo "=== Testing Immediate Effect of Happy Sensory Input ==="

# Reset the emotional state first (if possible)
echo "Sending a neutral message to establish baseline..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{input_type: \"text\", description: \"This is a neutral message for baseline\", source: \"test_script\", intensity: 0.5, priority: 0.5}'"

# Wait briefly to process
echo "Waiting 2 seconds for processing..."
sleep 2

# First, check the current emotional state
echo "Querying initial emotional state..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'" > "$RESULTS_DIR/direct_initial.txt"

echo "Initial state saved to $RESULTS_DIR/direct_initial.txt"

# Send an INTENSE happy sensory input
echo "Sending intense happy sensory input..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{input_type: \"text\", description: \"I am EXTREMELY HAPPY and joyful today!\", source: \"test_script\", intensity: 1.0, priority: 1.0}'"

# Wait minimal time for processing
echo "Waiting 1 second for processing..."
sleep 1

# Check the emotional state after sensory input
echo "Querying immediate updated emotional state..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'" > "$RESULTS_DIR/direct_updated.txt"

echo "Updated state saved to $RESULTS_DIR/direct_updated.txt"

echo "=== Test Complete ==="
echo "Running comparison analysis..."

# Run the comparison
python3 "$SCRIPT_DIR/direct_compare.py"

echo "Direct comparison complete!" 