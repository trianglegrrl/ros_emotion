FROM ros:foxy

# Set work directory
WORKDIR /ros_ws

# Copy our package
COPY ./ros_emotion /ros_ws/src/ros_emotion

# Make Python scripts executable
RUN find /ros_ws/src/ros_emotion/ros_emotion -name "*.py" -exec chmod +x {} \;

# Install dependencies and build the package
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-numpy \
    python3-yaml \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install requests \
    && cd /ros_ws \
    && . /opt/ros/$ROS_DISTRO/setup.sh \
    && colcon build --packages-select ros_emotion

# Create a launch script
RUN echo '#!/bin/bash\n\
source /opt/ros/$ROS_DISTRO/setup.bash\n\
source /ros_ws/install/setup.bash\n\
mkdir -p /root/.ros/log\n\
ros2 run ros_emotion emotional_state_manager.py &\n\
ros2 run ros_emotion sensory_input_processor.py &\n\
ros2 run ros_emotion llm_integration.py &\n\
ros2 run ros_emotion rumination_engine.py &\n\
ros2 run ros_emotion visualization_node.py &\n\
wait\n\
' > /ros_ws/launch_emotion_system.sh && chmod +x /ros_ws/launch_emotion_system.sh

# Add setup to entrypoint
RUN echo '. /ros_ws/install/setup.bash' >> /ros_entrypoint.sh

# Command to run when container starts
CMD ["/ros_ws/launch_emotion_system.sh"] 