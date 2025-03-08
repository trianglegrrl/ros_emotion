#!/bin/bash

# Build the Docker image
echo "Building the ros_emotion Docker image..."
docker build -t ros_emotion .

# Run the Docker container
echo "Starting the ros_emotion container..."
docker run -it --rm --name ros_emotion_container ros_emotion 