#!/bin/bash

# Start the test container
echo "Starting test container..."
docker-compose up -d ros_emotion_test

# Show logs
echo "Showing logs from ros_emotion_test_container..."
docker logs -f ros_emotion_test_container 