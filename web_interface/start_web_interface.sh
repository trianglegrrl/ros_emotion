#!/bin/bash

# Build the Docker image
echo "Building the ros_web_interface Docker image..."
docker build -t ros_web_interface .

# Run the Docker container
echo "Starting the ros_web_interface container..."
docker run -it --rm \
  --name ros_web_interface_container \
  --network="host" \
  -p 9999:9999 \
  ros_web_interface bash -c "tail -f /dev/null" 