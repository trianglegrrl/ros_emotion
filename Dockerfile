FROM ros:foxy

# Set work directory
WORKDIR /ros_ws

# Copy our package
COPY ./ros_emotion /ros_ws/src/ros_emotion

# Install dependencies and build the package
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && cd /ros_ws \
    && . /opt/ros/$ROS_DISTRO/setup.sh \
    && colcon build --packages-select ros_emotion

# Add setup to entrypoint
RUN echo '. /ros_ws/install/setup.bash' >> /ros_entrypoint.sh

# Command to run when container starts
CMD ["bash", "-c", "source /ros_ws/install/setup.bash && ros2 launch ros_emotion emotion_publisher.launch.py"] 