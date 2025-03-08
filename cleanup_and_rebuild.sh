#!/bin/bash

echo "Cleaning up all existing containers..."
# Stop and remove any existing containers
docker stop ros_emotion_container ros_web_interface_container ros_test_publisher_container || true
docker rm ros_emotion_container ros_web_interface_container ros_test_publisher_container || true

# Also remove any containers based on our images
docker rm $(docker ps -aq --filter ancestor=ros_emotion --filter ancestor=ros_web_interface --filter ancestor=ros_test_publisher) 2>/dev/null || true

echo "Removing all related Docker images..."
# Remove all related Docker images to ensure clean rebuild
docker rmi ros_emotion ros_web_interface ros_test_publisher 2>/dev/null || true

echo "Rebuilding everything from scratch..."

# Build and start the containers
echo "Building and starting the containers with Docker Compose..."
docker-compose build --no-cache
docker-compose up -d

echo ""
echo "ROS Emotion system has been rebuilt and is running!"
echo "Access the web interface at: http://localhost:9999"
echo ""
echo "To stop the containers, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f" 