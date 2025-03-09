#!/usr/bin/env python3

import subprocess
import json
import time
import sys
import os

# Config file path
CONFIG_FILE = "emotion_config_slow_decay.json"

def run_command(cmd):
    """Execute a shell command in the Docker container."""
    full_cmd = f'docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && {cmd}"'
    try:
        result = subprocess.run(full_cmd, shell=True, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error output: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Exception while running command: {e}")
        return None

def send_sensory_input(message, intensity=1.0, priority=1.0):
    """Send a sensory input with the given message."""
    # Properly escape any special characters in the message
    escaped_message = message.replace('"', '\\"')
    
    # Use single quotes around the entire command and double quotes for the message
    cmd = f"ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{{input_type: \"text\", description: \"{escaped_message}\", source: \"test_script\", intensity: {intensity}, priority: {priority}}}'"
    
    output = run_command(cmd)
    if output:
        print("Message sent successfully")
    return output

def query_emotional_state():
    """Query the current emotional state."""
    cmd = 'ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery \'{query_type: "full", specific_emotion: "", include_description: true}\''
    return run_command(cmd)

def create_slow_decay_config():
    """Create a configuration file with very slow decay rates."""
    # Define the configuration with slow decay rates
    config = {
        "emotional_state_manager": {
            "personality": {
                "default_decay_rates": {
                    "happiness": 0.005,  # 10x slower
                    "sadness": 0.003,    # 10x slower
                    "anger": 0.004,      # 10x slower
                    "fear": 0.004,       # 10x slower
                    "disgust": 0.003,    # 10x slower
                    "surprise": 0.008,   # 10x slower
                    "pleasure": 0.005,   # 10x slower
                    "arousal": 0.004,    # 10x slower
                    "dominance": 0.003   # 10x slower
                }
            }
        }
    }
    
    # Write the configuration to a file
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Created slow decay configuration file: {CONFIG_FILE}")
    
    # Copy the file to the container
    subprocess.run(f"docker cp {CONFIG_FILE} ros_emotion_container:/ros_ws/src/ros_emotion/ros_emotion/config/", shell=True)
    print("Copied configuration file to container")

def restart_emotional_state_manager():
    """Restart the emotional state manager to apply the new configuration."""
    # First, kill the existing node
    run_command("ros2 lifecycle set /emotional_state_manager shutdown")
    time.sleep(1)
    
    # Start it with the new configuration
    run_command("ros2 run ros_emotion emotional_state_manager --ros-args -p config_file:=emotion_config_slow_decay.json")
    time.sleep(2)
    
    print("Emotional state manager restarted with slow decay configuration")

def reset_configuration():
    """Reset to the default configuration."""
    # First, kill the node with slow decay
    run_command("ros2 lifecycle set /emotional_state_manager shutdown")
    time.sleep(1)
    
    # Restart with default configuration
    run_command("ros2 run ros_emotion emotional_state_manager")
    time.sleep(2)
    
    print("Emotional state manager reset to default configuration")

def test_happy_input_with_slow_decay():
    """Test happy input with slow decay rates."""
    # Create and apply slow decay configuration
    create_slow_decay_config()
    restart_emotional_state_manager()
    
    try:
        # Get baseline emotional state
        print("\n=== Baseline Emotional State (Slow Decay) ===")
        baseline_output = query_emotional_state()
        print(baseline_output)
        
        # Send happy input
        print("\n=== Sending Happy Input ===")
        send_sensory_input("I am extremely happy and joyful today!", 1.0, 1.0)
        
        # Wait a moment for processing
        time.sleep(1)
        
        # Query immediately after
        print("\n=== Emotional State Immediately After Happy Input ===")
        immediate_output = query_emotional_state()
        print(immediate_output)
        
        # Wait longer to show slow decay
        print("\n=== Waiting 5 seconds to show slow decay ===")
        time.sleep(5)
        
        # Query after waiting
        print("\n=== Emotional State 5 Seconds After Happy Input (Should Show Slow Decay) ===")
        delayed_output = query_emotional_state()
        print(delayed_output)
        
        # Wait even longer
        print("\n=== Waiting 10 more seconds to show continued slow decay ===")
        time.sleep(10)
        
        # Query after longer wait
        print("\n=== Emotional State 15 Seconds After Happy Input ===")
        final_output = query_emotional_state()
        print(final_output)
        
    finally:
        # Always reset to default configuration
        reset_configuration()
        
        # Clean up the configuration file
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)

if __name__ == "__main__":
    print("=== TESTING HAPPY INPUT WITH SLOWED DECAY RATES ===")
    test_happy_input_with_slow_decay()
    print("\nTest complete!") 