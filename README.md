# ROS Emotion System

A sophisticated robotic emotional intelligence system built on ROS 2, with dynamic personality traits, sensory processing, emotional state management, and natural language integration.

## Overview

The ROS Emotion System provides robots with the ability to:
- Process and respond emotionally to sensory inputs
- Maintain a dynamic emotional state that naturally decays over time
- Develop personality traits that influence emotional responses
- Process natural language inputs using OpenAI's language models
- Visualize emotional states through a web interface
- Engage in rumination about past experiences

## Quick Start

To start the entire system:

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env to add your OpenAI API key

# Start all containers
./start_all.sh
```

Access the web interface at:
- http://localhost:9999

To stop everything:

```bash
docker-compose down
```

For rebuilding after changes:

```bash
./cleanup_and_rebuild.sh
```

## Documentation

The system is divided into several modules with detailed documentation:

- [**OpenAI Integration**](OpenAI_INTEGRATION.md) - Setup and usage of the OpenAI LLM integration
- [**Testing Documentation**](TESTING.md) - Guides for testing the emotion system
- [**ROS Emotion Package**](ros_emotion/README.md) - Core ROS package documentation

## System Components

- **Emotional State Manager**: Maintains the current emotional state
- **Personality Model**: Influences how emotions are processed
- **Sensory Input Processor**: Processes various sensory inputs
- **LLM Integration**: Connects with OpenAI for natural language processing
- **Rumination Engine**: Processes emotions over time
- **Web Interface**: Visualizes the emotional state

## Testing

The system includes comprehensive testing tools located in the `testing/` directory:

```bash
# Run the optimal emotion test
./optimal_emotion_test.py
```

See [TESTING.md](TESTING.md) for detailed information about testing the system.

## Development

To extend the system:

1. Add new nodes in the `ros_emotion` directory
2. Update launch files to include your new nodes
3. Rebuild using the cleanup_and_rebuild.sh script

## Structure

```
ros_emotion/
├── Dockerfile                   # Main ROS container
├── docker-compose.yml          # Container orchestration
├── OpenAI_INTEGRATION.md       # OpenAI setup documentation
├── TESTING.md                  # Testing documentation
├── web_interface/              # Web visualization interface
│   ├── Dockerfile              # Web container
│   └── web/                    # Web files
├── ros_emotion/                # ROS package
│   ├── config/                 # Configuration files
│   ├── launch/                 # Launch files
│   ├── msg/                    # Message definitions
│   ├── srv/                    # Service definitions
│   └── ros_emotion/            # Python modules
└── testing/                    # Testing tools
    ├── scripts/                # Test scripts
    ├── results/                # Test results
    └── docs/                   # Testing documentation
```

## Requirements

- Docker
- Docker Compose
- OpenAI API key (for LLM integration)

## Viewing Messages

To see the published messages, you can run another container that subscribes to the `emotion` topic:

```bash
docker run -it --rm --network=host ros:foxy ros2 topic echo /emotion
```

Note: This requires the `--network=host` option to connect to the publisher container. 