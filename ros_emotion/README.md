# ROS Emotion Package

A ROS 2 package for robot emotion processing, providing a comprehensive system for maintaining and updating emotional states based on sensory inputs.

## Overview

The `ros_emotion` package implements a robot emotion processing system with the following components:

1. **Emotional State Manager**: Maintains and updates the robot's emotional state
2. **Sensory Input Processor**: Processes different types of sensory inputs
3. **LLM Integration**: Integrates with a Large Language Model to process natural language descriptions
4. **Rumination Engine**: Allows for gradual processing of emotional responses
5. **Visualization Node**: Provides visualization tools for monitoring emotional states

## Emotional Model

The package uses a hybrid emotional model combining:

- **Dimensional Model (PAD)**: Pleasure, Arousal, Dominance
- **Basic Emotions**: Happiness, Sadness, Anger, Fear, Disgust, Surprise

## Installation

### Prerequisites

- ROS 2 Foxy or newer
- Python 3.8 or newer
- Required Python packages: `numpy`, `requests`, `pyyaml`

### Building from Source

```bash
# Create a ROS workspace (if you don't have one)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# Clone the repository
git clone https://github.com/yourusername/ros_emotion.git

# Install dependencies
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y

# Build the package
colcon build --packages-select ros_emotion

# Source the workspace
source ~/ros2_ws/install/setup.bash
```

## Usage

### Running the Emotion System

```bash
# Launch the complete emotion system
ros2 launch ros_emotion emotion_publisher.launch.py

# Launch with test input publisher
ros2 launch ros_emotion emotion_test.launch.py
```

### Publishing Sensory Inputs

You can publish sensory inputs to the system using the following topics:

- **Text Input**: `text_input` (std_msgs/String)
- **Visual Input**: `visual_input` (std_msgs/String)
- **Auditory Input**: `auditory_input` (std_msgs/String)
- **Touch Input**: `touch_input` (std_msgs/String)

Example:

```bash
# Publish a text input
ros2 topic pub /text_input std_msgs/msg/String "data: '{\"description\": \"The robot receives a compliment\", \"intensity\": 0.8}'"
```

### Querying Emotional State

You can query the current emotional state using the `query_emotional_state` service:

```bash
# Query the full emotional state
ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery "{query_type: 'full', include_description: true}"

# Query only the dimensional model
ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery "{query_type: 'dimensional', include_description: false}"

# Query only the categorical emotions
ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery "{query_type: 'categorical', include_description: false}"

# Query a specific emotion
ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery "{query_type: 'specific', specific_emotion: 'happiness', include_description: false}"
```

### Modifying Emotional State

You can modify the emotional state using the `modify_emotional_state` service:

```bash
# Reset the emotional state
ros2 service call /modify_emotional_state ros_emotion/srv/EmotionModify "{modification_type: 'reset', reason: 'Testing', override_safety: false}"

# Set all emotions to a specific value
ros2 service call /modify_emotional_state ros_emotion/srv/EmotionModify "{modification_type: 'absolute', value: 0.5, reason: 'Testing', override_safety: false}"

# Adjust all emotions by a relative amount
ros2 service call /modify_emotional_state ros_emotion/srv/EmotionModify "{modification_type: 'relative', value: 0.2, reason: 'Testing', override_safety: false}"

# Modify a specific emotion
ros2 service call /modify_emotional_state ros_emotion/srv/EmotionModify "{modification_type: 'specific', specific_emotion: 'happiness', value: 0.8, reason: 'Testing', override_safety: false}"
```

## Configuration

The package can be configured using the YAML file in the `config` directory:

- `emotion_config.yaml`: Contains configuration for all components of the emotion system

## Visualization

The visualization node publishes visualization markers to the `emotion_visualization` topic, which can be viewed in RViz.

To view the visualization:

1. Launch RViz: `ros2 run rviz2 rviz2`
2. Add a MarkerArray display
3. Set the topic to `/emotion_visualization`
4. Set the fixed frame to `emotion_frame`

## License

This package is licensed under the MIT License - see the LICENSE file for details. 