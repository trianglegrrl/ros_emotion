cmake_minimum_required(VERSION 3.5)
project(ros_emotion)

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(action_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generate interfaces
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EmotionalState.msg"
  "msg/SensoryInput.msg"
  "msg/RuminationUpdate.msg"
  "msg/EmotionalResponse.msg"
  "srv/EmotionQuery.srv"
  "srv/EmotionModify.srv"
  "srv/NodeLifecycle.srv"
  DEPENDENCIES builtin_interfaces std_msgs
)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

# Install Python executables
install(PROGRAMS
  ros_emotion/emotional_state_manager.py
  ros_emotion/sensory_input_processor.py
  ros_emotion/llm_integration.py
  ros_emotion/rumination_engine.py
  ros_emotion/visualization_node.py
  ros_emotion/test_input_publisher.py
  ros_emotion/node_lifecycle_manager.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch files
install(DIRECTORY
  launch
  config
  DESTINATION share/${PROJECT_NAME}
)

ament_package() 