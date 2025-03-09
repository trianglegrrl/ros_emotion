#!/bin/bash

# Start all containers
echo "Starting all containers..."
docker-compose up -d

# Start the feature flags manager in the container
echo "Starting feature flags manager..."
docker-compose exec -d ros_emotion bash -c 'source /opt/ros/$ROS_DISTRO/setup.bash && source /ros_ws/install/setup.bash && ros2 run ros_emotion feature_flags_manager'

echo "Feature flags manager should now be running"
echo "Showing logs from ros_emotion_container..."
docker-compose logs -f ros_emotion

echo ""
echo "ROS Emotion system is running!"
echo "Access the web interface at: http://localhost:9999"
echo ""
echo "To stop the containers, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f" 