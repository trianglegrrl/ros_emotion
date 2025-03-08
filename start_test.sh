#!/bin/bash

# Build the test Docker image
echo "Building the test publisher Docker image..."
docker build -t ros_test_publisher -f Dockerfile.test .

# Run the Docker container
echo "Starting the test publisher container..."
docker run -it --rm --name ros_test_publisher_container --network="host" ros_test_publisher 