# ROS Emotion Package

A simple ROS 2 package that publishes "Hello World" messages to the `emotion` topic every 5 seconds, with a web interface to view ROS topics.

## Requirements

- Docker
- Docker Compose (for running both containers together)

## Quick Start (All-in-One)

To start both the ROS publisher and web interface containers at once:

```bash
./start_all.sh
```

This will:
1. Build both Docker images
2. Start both containers
3. Make the web interface available at http://localhost:9999

To stop everything:

```bash
docker-compose down
```

## Individual Container Setup

If you prefer to run the containers individually:

### ROS Publisher Container

```bash
./start_container.sh
```

### Web Interface Container

```bash
cd web_interface
./start_web_interface.sh
```

Once started, you can access the web interface at:
- http://localhost:9999

The web interface allows you to:
- View all available ROS topics
- Subscribe to topics to see their messages in real-time
- Refresh the topic list

## Manual Setup

If you prefer to run the commands manually without scripts:

### Build and Run the ROS Publisher

```bash
docker build -t ros_emotion .
docker run -it --rm --name ros_emotion_container ros_emotion
```

### Build and Run the Web Interface

```bash
cd web_interface
docker build -t ros_web_interface .
docker run -it --rm --name ros_web_interface_container -p 9999:9999 --network=host ros_web_interface
```

## Development

The package contains a simple ROS 2 publisher node that publishes to the `emotion` topic. You can extend this package by:

1. Adding more nodes in the `ros_emotion` directory
2. Updating the launch file to include your new nodes
3. Rebuilding the Docker image

## Structure

```
ros_emotion/
├── Dockerfile                   # ROS publisher container
├── docker-compose.yml          # Compose file for both containers
├── start_container.sh          # Script to start ROS publisher
├── start_all.sh                # Script to start both containers
├── web_interface/              # Web interface files
│   ├── Dockerfile              # Web interface container
│   ├── entrypoint.sh           # Web container entrypoint
│   ├── start_web_interface.sh  # Script to start web interface
│   └── web/                    # Web files
│       └── index.html          # Web interface HTML
├── ros_emotion/                # ROS package
│   ├── launch/                 # Launch files
│   │   └── emotion_publisher.launch.py
│   ├── resource/               # Package resources
│   │   └── ros_emotion
│   ├── ros_emotion/            # Python package
│   │   ├── __init__.py
│   │   └── publisher_node.py   # Publisher node
│   ├── package.xml             # Package metadata
│   └── setup.py                # Package setup
```

## Viewing Messages

To see the published messages, you can run another container that subscribes to the `emotion` topic:

```bash
docker run -it --rm --network=host ros:foxy ros2 topic echo /emotion
```

Note: This requires the `--network=host` option to connect to the publisher container. 