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

## Emotion Model Architecture

The system uses an abstract `EmotionModel` class as the core interface for all emotion-related operations. This design provides:

- **Abstraction**: Separates the implementation details from how emotional states are used
- **Extensibility**: New emotion models can be implemented by extending the base class
- **Consistency**: Ensures all components interact with emotions in a standardized way

### EmotionModel Interface

The `EmotionModel` class provides the following key methods:

- **create_emotional_state()**: Creates a new emotional state with default values
- **get_primary_emotion()**: Determines the primary emotion from the current state
- **update_state()**: Updates the state based on decay rates over time
- **modify_state()**: Modifies the state based on various modification types
- **get_all_emotions()**: Returns a list of all supported emotions
- **get_dimensions()**: Returns a list of all emotional dimensions (e.g., PAD)
- **get_emotion_value()**: Gets the value of a specific emotion
- **set_emotion_value()**: Sets the value of a specific emotion
- **calculate_intensity()**: Calculates the overall intensity of the state
- **get_emotion_color()**: Gets a color representing a specific emotion
- **format_emotional_state()**: Formats the emotional state for display/prompts
- **get_emotional_state_color()**: Gets a color representing the full emotional state

### Built-in Emotion Models

#### PADBasicEmotionModel

The default implementation uses the `PADBasicEmotionModel` which combines:

- **PAD Dimensional Model**: Pleasure (-1.0 to 1.0), Arousal (-1.0 to 1.0), Dominance (-1.0 to 1.0)
- **Basic Emotions**: Happiness, Sadness, Anger, Fear, Disgust, Surprise (0.0 to 1.0)

The model handles:
- Determining primary emotions based on the highest basic emotion value
- Calculating intensity based on both PAD dimensions and basic emotions
- Mapping emotions to colors for visualization
- Managing the relationship between dimensional and categorical emotion representations

### Creating Custom Emotion Models

To create a custom emotion model:

1. Create a new class that extends `EmotionModel`
2. Implement all the required abstract methods
3. Register your model in the `create_emotion_model()` factory function
4. Update the configuration to use your custom model

Example configuration in `emotion_config.yaml`:
```yaml
emotional_state_manager:
  emotion_model: "your_custom_model"
```

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

### Docker Deployment

This package includes Docker support for easy deployment and testing:

```bash
# Build and start all containers
./cleanup_and_rebuild.sh

# Start containers if already built
./start_all.sh

# Stop all containers
docker-compose down
```

The Docker deployment includes:
- Main ROS container with all nodes
- Test container for running tests
- Web interface container for visualization

## Usage

### Running the Emotion System

To run the entire system:

```bash
# Using scripts (recommended)
./start_all.sh

# Or manually
docker-compose up
```

For development and testing:

```bash
# Rebuild and restart all containers
./cleanup_and_rebuild.sh
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

# Using Docker
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{input_type: \"visual\", description: \"I see a cute puppy playing\", source: \"visual_sensor\", intensity: 0.8}'"
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

### Monitoring Emotional State

You can monitor the emotional state by echoing the `/emotional_state` topic:

```bash
# Using Docker
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic echo /emotional_state"
```

## Configuration

The package can be configured using the YAML file in the `config` directory:

- `emotion_config.yaml`: Contains configuration for all components of the emotion system, including:
  - Emotion model type and parameters
  - Default decay rates for emotions
  - Rumination parameters
  - Visualization settings

## Visualization

The visualization node publishes visualization markers to the `emotion_visualization` topic, which can be viewed in RViz.

To view the visualization:

1. Launch RViz: `ros2 run rviz2 rviz2`
2. Add a MarkerArray display
3. Set the topic to `/emotion_visualization`
4. Set the fixed frame to `emotion_frame`

## Development

### System Architecture

The system uses a modular architecture with the following key components:

1. **EmotionModel**: Core abstraction for emotion processing
2. **EmotionalStateManager**: Maintains and updates the emotional state
3. **LLMIntegration**: Interfaces with LLMs to process inputs
4. **RuminationEngine**: Processes emotional inputs over time
5. **VisualizationNode**: Provides visualization of the emotional state

### Adding New Features

#### Extending the Emotion Model

To extend with a new emotion model:

1. Create a new class that extends `EmotionModel` in `emotion_model.py`
2. Implement all required abstract methods
3. Register your model in the `create_emotion_model()` factory function
4. Update config to use your new model

#### Adding New Sensory Input Types

To add new input types:

1. Add a new callback method in `sensory_input_processor.py`
2. Register the new subscriber in the constructor
3. Update the `process_input()` method to handle the new input type

#### Customizing Visualization

To customize the visualization:

1. Modify the marker creation methods in `visualization_node.py`
2. Update the `get_emotional_state_color()` method in your emotion model

### Testing

The package includes a test input publisher for testing the system:

```bash
# Start the test input publisher
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 run ros_emotion test_input_publisher.py"
```

## License

This package is licensed under the MIT License - see the LICENSE file for details. 