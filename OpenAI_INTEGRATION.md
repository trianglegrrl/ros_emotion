# OpenAI Integration for ROS Emotion System

This guide explains how to set up and use the OpenAI integration for the ROS Emotion system.

## Setup

1. **Get an OpenAI API Key**
   - Sign up for an account at [OpenAI](https://platform.openai.com)
   - Navigate to the API keys section in your account
   - Create a new API key

2. **Configure Environment Variables**
   - Edit the `.env` file in the root directory of the project
   - Replace `replace_with_your_actual_api_key` with your actual OpenAI API key:
     ```
     OPENAI_API_KEY=your_actual_api_key_here
     ```
   - Optionally, change the model to use:
     ```
     OPENAI_MODEL=gpt-4o-mini
     ```
     (Other options include: `gpt-4-turbo`, `gpt-3.5-turbo`)

3. **Rebuild and Restart Containers**
   - Run the cleanup and rebuild script:
     ```
     ./cleanup_and_rebuild.sh
     ```
   - Or manually restart:
     ```
     docker-compose down
     docker-compose build
     docker-compose up -d
     ```

## How It Works

The integration uses OpenAI's models to process sensory inputs and determine appropriate emotional responses:

1. When a sensory input is received, it's passed to the LLM integration node
2. The node constructs a prompt containing:
   - Current emotional state
   - Personality profile
   - Sensory input details
   - Active goals

3. The OpenAI model analyzes this data and returns:
   - Proposed changes to pleasure, arousal, and dominance dimensions
   - Recommended primary emotion
   - Response text explaining the emotional change

4. These changes are applied to the emotional state, influenced by personality traits

## Testing

To test the OpenAI integration:

1. Send a sensory input:
   ```
   docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{input_type: \"text\", description: \"I am feeling excited about this new project!\", source: \"test\", intensity: 0.8, priority: 0.7}'"
   ```

2. Check the emotional state:
   ```
   docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'"
   ```

3. View logs to see the LLM processing:
   ```
   docker logs -f ros_emotion_container | grep "ALAINA"
   ```

## Debugging

If you encounter issues:

1. **Check API Key**: Ensure your API key is correctly set in the `.env` file
2. **Check Logs**: Look for errors in the container logs
3. **Check Network**: Ensure the container has network access to reach OpenAI's API
4. **Model Availability**: Confirm the model you're using is available in your OpenAI account

## Advanced Configuration

You can modify advanced settings in `ros_emotion/config/emotion_config.yaml`:

- Change prompt templates
- Adjust temperature (creativity) of the LLM responses
- Configure max tokens for responses
- Change processing frequency 