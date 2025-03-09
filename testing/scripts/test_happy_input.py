#!/usr/bin/env python3

import subprocess
import json
import time
import sys

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

def query_emotional_state():
    """Query the current emotional state."""
    print("Querying current emotional state...")
    cmd = 'ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery \'{query_type: "full", specific_emotion: "", include_description: true}\''
    output = run_command(cmd)
    
    if not output:
        print("Failed to query emotional state.")
        return None
    
    # Parse the output to extract emotional values
    try:
        # Extract the result portion
        lines = output.strip().split('\n')
        result_start = False
        result_lines = []
        
        for line in lines:
            if "result:" in line:
                result_start = True
            if result_start:
                result_lines.append(line)
        
        # Parse pleasure, arousal, dominance
        pleasure, arousal, dominance = None, None, None
        happiness = None
        description = None
        
        for line in result_lines:
            if "pleasure:" in line:
                pleasure = float(line.split("pleasure:")[1].strip())
            elif "arousal:" in line:
                arousal = float(line.split("arousal:")[1].strip())
            elif "dominance:" in line:
                dominance = float(line.split("dominance:")[1].strip())
            elif "happiness:" in line:
                happiness = float(line.split("happiness:")[1].strip())
            elif "description:" in line:
                description = line.split("description:")[1].strip().strip('"')
        
        return {
            "pleasure": pleasure,
            "arousal": arousal,
            "dominance": dominance,
            "happiness": happiness,
            "description": description
        }
    
    except Exception as e:
        print(f"Error parsing emotional state: {e}")
        print(f"Raw output: {output}")
        return None

def send_happy_input(intensity=0.7, priority=0.6):
    """Send a sensory input with 'happy' content."""
    print("Sending 'happy' sensory input...")
    
    happy_input = "I feel very happy and content today"
    
    # Simplified command with fewer nested quotes
    cmd = 'ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput "{input_type: \\"text\\", description: \\"' + happy_input + '\\", source: \\"test_script\\", intensity: ' + str(intensity) + ', priority: ' + str(priority) + '}"'
    
    output = run_command(cmd)
    if not output:
        print("Failed to send sensory input.")
        return False
    
    print("Sensory input sent successfully.")
    return True

def test_emotional_response():
    """Test that sensory input with 'happy' increases pleasure and happiness."""
    # 1. Get baseline emotional state
    print("\n=== BASELINE EMOTIONAL STATE ===")
    baseline = query_emotional_state()
    if not baseline:
        print("Could not get baseline emotional state. Exiting.")
        return False
    
    print(f"Baseline pleasure: {baseline['pleasure']}")
    print(f"Baseline happiness: {baseline['happiness']}")
    print(f"Baseline description: {baseline['description']}")
    
    # 2. Send happy input
    if not send_happy_input():
        print("Failed to send happy input. Exiting.")
        return False
    
    # 3. Wait for processing (adjust based on your system's processing time)
    print("\nWaiting for emotional state to update...")
    time.sleep(5)
    
    # 4. Get updated emotional state
    print("\n=== UPDATED EMOTIONAL STATE ===")
    updated = query_emotional_state()
    if not updated:
        print("Could not get updated emotional state. Exiting.")
        return False
    
    print(f"Updated pleasure: {updated['pleasure']}")
    print(f"Updated happiness: {updated['happiness']}")
    print(f"Updated description: {updated['description']}")
    
    # 5. Compare and report
    pleasure_change = updated['pleasure'] - baseline['pleasure']
    happiness_change = updated['happiness'] - baseline['happiness']
    
    print("\n=== RESULTS ===")
    print(f"Pleasure change: {pleasure_change:.4f}")
    print(f"Happiness change: {happiness_change:.4f}")
    
    # Check if values increased (allow for small floating point imprecision)
    if pleasure_change > 0.001:
        print("SUCCESS: Pleasure increased as expected.")
    else:
        print("WARNING: Pleasure did not increase.")
    
    if happiness_change > 0.001:
        print("SUCCESS: Happiness increased as expected.")
    else:
        print("WARNING: Happiness did not increase.")
    
    return pleasure_change > 0.001 and happiness_change > 0.001

if __name__ == "__main__":
    print("=== Testing Emotional Response to 'Happy' Input ===")
    success = test_emotional_response()
    
    if success:
        print("\nTest PASSED: Emotional state responded correctly to 'happy' input.")
        sys.exit(0)
    else:
        print("\nTest WARNING: Emotional state may not have responded as expected.")
        sys.exit(1) 