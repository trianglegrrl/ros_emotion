#!/bin/bash

# Stop all containers
echo "Stopping all containers..."
docker-compose down

# Remove all images
echo "Removing Docker images..."
docker rmi $(docker images -q ros_emotion_*) 2>/dev/null || true

# Rebuild and start
echo "Rebuilding and starting containers..."
docker-compose build
docker-compose up -d

# Show logs
echo "Showing logs from ros_emotion_container..."
docker logs -f ros_emotion_container

echo ""
echo "ROS Emotion system has been rebuilt and is running!"
echo "Access the web interface at: http://localhost:9999"
echo ""
echo "To stop the containers, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f" 