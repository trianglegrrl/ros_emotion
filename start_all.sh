#!/bin/bash

# Build and start both containers using Docker Compose
echo "Starting ROS Emotion and Web Interface containers..."
docker-compose up -d

echo ""
echo "ROS Emotion system is running!"
echo "Access the web interface at: http://localhost:9999"
echo ""
echo "To stop the containers, run: docker-compose down" 