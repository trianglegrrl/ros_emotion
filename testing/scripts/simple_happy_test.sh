#!/bin/bash

echo "=== Testing Happy Sensory Input ==="

# First, check the current emotional state
echo "Querying initial emotional state..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'" > initial_state.txt

echo "Initial state saved to initial_state.txt"

# Send happy sensory input
echo "Sending happy sensory input..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{input_type: \"text\", description: \"I feel very happy and content today\", source: \"test_script\", intensity: 0.7, priority: 0.6}'"

# Wait for the system to process the input
echo "Waiting 5 seconds for processing..."
sleep 5

# Check the emotional state after sensory input
echo "Querying updated emotional state..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'" > updated_state.txt

echo "Updated state saved to updated_state.txt"

echo "=== Test Complete ==="
echo "Please compare initial_state.txt and updated_state.txt to see if pleasure and happiness increased." 