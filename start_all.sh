#!/bin/bash

# Start all containers
echo "Starting all containers..."
docker-compose up -d

# Show logs
echo "Showing logs from ros_emotion_container..."
docker logs -f ros_emotion_container

echo ""
echo "ROS Emotion system is running!"
echo "Access the web interface at: http://localhost:9999"
echo ""
echo "To stop the containers, run: docker-compose down" 