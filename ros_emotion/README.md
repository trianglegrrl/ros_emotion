# ROS Emotion System

This package provides a comprehensive emotional processing system for robots using ROS 2. It incorporates emotional state management, sensory input processing, rumination, and integration with language models (LLMs) to create a sophisticated emotional architecture.

## Features

- **Emotional State Management**: Manages emotional state using a PAD (Pleasure, Arousal, Dominance) dimensional model combined with basic emotions.
- **Personality Modeling**: Incorporates personality traits that influence emotional responses and processing.
- **Sensory Input Processing**: Processes various types of sensory inputs (visual, auditory, text, touch).
- **Rumination Engine**: Simulates internal thought processes that continue to influence emotional state.
- **LLM Integration**: Uses language models to generate emotional responses to inputs.
- **Visualization**: Provides visual representation of the emotional state.

## Architecture

The system consists of several interconnected nodes:

1. **Emotional State Manager**: Maintains the current emotional state, applies decay over time, and handles requests to modify the state.
2. **Sensory Input Processor**: Processes incoming sensory data and forwards it for emotional processing.
3. **LLM Integration**: Interfaces with language models to determine emotional responses to inputs.
4. **Rumination Engine**: Simulates continued internal processing of experiences, generating ongoing emotional responses.
5. **Visualization Node**: Provides visual representations of the emotional state.
6. **Node Lifecycle Manager**: Controls the lifecycle of all nodes in the system.

## Personality Model

The system now includes a sophisticated personality model that influences how emotions are processed, expressed, and decay over time.

### Key Components

#### PersonalityModel Abstract Class

The `PersonalityModel` abstract class defines the interface for personality models:

- **Trait Management**: Methods to initialize, get, and set personality traits.
- **Emotional Influence**: Methods to modulate emotional responses and influence emotional states.
- **Goal-Oriented Behavior**: Methods to adjust emotional states based on current goals.
- **Configuration**: Methods to provide baselines and decay rates influenced by personality.

#### HybridPersonalityModel Implementation

The `HybridPersonalityModel` is a concrete implementation that combines:

- **Five-Factor Model (OCEAN)**:
  - **Openness**: Influences curiosity, creativity, and receptiveness to new experiences.
  - **Conscientiousness**: Affects orderliness, responsibility, and goal-directed behavior.
  - **Extraversion**: Impacts social engagement, positive emotions, and activity levels.
  - **Agreeableness**: Influences cooperation, empathy, and conflict avoidance.
  - **Neuroticism**: Affects emotional stability, anxiety, and reactivity to stimuli.

- **Goal-Oriented Behavior**:
  - Adjusts emotional responses based on current goals (safety, social, achievement, etc.).
  - Personality traits modulate the importance and influence of different goals.

- **Emotional Processing**:
  - Influences baseline emotional states (e.g., higher neuroticism = higher baseline anxiety).
  - Modulates the intensity of emotional responses.
  - Affects decay rates of different emotions (e.g., extraverts' negative emotions decay faster).

### Integration Points

The personality model is integrated with multiple components:

1. **Emotional State Manager**: Applies personality influences to emotional states and incorporates goals.
2. **LLM Integration**: Includes personality context in prompts for more accurate emotional responses.
3. **Rumination Engine**: Adjusts rumination intensity and continuation based on personality traits.

### Customization

The personality model can be customized through configuration:

```yaml
personality:
  traits:
    openness: 0.7        # Higher openness to experience
    conscientiousness: 0.6
    extraversion: 0.8    # More extraverted
    agreeableness: 0.5
    neuroticism: 0.3     # More emotionally stable
    risk_tolerance: 0.6  # Custom trait
    
  goals:
    safety: 0.5
    social: 0.8          # Strong focus on social interaction
    achievement: 0.7
    exploration: 0.6
    stability: 0.4
```

## Installation

### Prerequisites

- ROS 2 Foxy
- Python 3.8+
- Docker (optional)

### Building from Source

1. Clone the repository into your ROS 2 workspace's `src` directory:
   ```
   cd ~/ros2_ws/src
   git clone https://github.com/yourusername/ros_emotion.git
   ```

2. Install dependencies:
   ```
   cd ~/ros2_ws
   rosdep install --from-paths src --ignore-src -r -y
   ```

3. Build the package:
   ```
   colcon build --symlink-install --packages-select ros_emotion
   ```

4. Source the workspace:
   ```
   source ~/ros2_ws/install/setup.bash
   ```

### Docker Setup

Alternatively, use the provided Docker setup:

1. Build the Docker images:
   ```
   ./cleanup_and_rebuild.sh
   ```

2. Start the containers:
   ```
   ./start_all.sh
   ```

## Usage

### Starting the System

Start the complete emotion system with personality model:

```
ros2 launch ros_emotion emotion_system_with_personality.launch.py
```

You can customize the personality model type:

```
ros2 launch ros_emotion emotion_system_with_personality.launch.py personality_type:=hybrid
```

### Sending Test Inputs

The system includes a test input publisher that can be used to send various types of inputs:

```
ros2 run ros_emotion test_input_publisher.py
```

### Querying Emotional State

Query the current emotional state:

```
ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery "query_type: 'full' specific_emotion: '' include_description: true"
```

### Modifying Personality Traits

Modify personality traits through the emotion modify service:

```
ros2 service call /modify_emotional_state ros_emotion/srv/EmotionModify "modification_type: 'personality_trait' specific_emotion: 'neuroticism' value: 0.8 reason: 'Testing personality influence' override_safety: false"
```

## Configuration

The system can be configured using the `emotion_config.yaml` file:

```yaml
emotional_state_manager:
  update_frequency: 10.0
  emotion_model_type: "pad_basic"
  personality_model_type: "hybrid"
  personality:
    traits:
      openness: 0.6
      conscientiousness: 0.5
      extraversion: 0.7
      agreeableness: 0.6
      neuroticism: 0.4
    goals:
      safety: 0.7
      social: 0.6
      achievement: 0.8
      exploration: 0.5
      stability: 0.6
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Five-Factor Model (OCEAN) implementation is based on psychological research by Costa and McCrae.
- The PAD emotional model is based on the work of Mehrabian and Russell. 