#!/usr/bin/env python3

import subprocess
import json
import time
import sys
import re

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

def extract_emotional_values(state_output):
    """Extract emotional values from the service output."""
    if not state_output:
        return None
    
    # Extract all emotional values using regex
    pleasure_match = re.search(r'pleasure=(-?[0-9.]+)', state_output)
    arousal_match = re.search(r'arousal=(-?[0-9.]+)', state_output)
    dominance_match = re.search(r'dominance=(-?[0-9.]+)', state_output)
    happiness_match = re.search(r'happiness=(-?[0-9.]+)', state_output)
    sadness_match = re.search(r'sadness=(-?[0-9.]+)', state_output)
    anger_match = re.search(r'anger=(-?[0-9.]+)', state_output)
    fear_match = re.search(r'fear=(-?[0-9.]+)', state_output)
    disgust_match = re.search(r'disgust=(-?[0-9.]+)', state_output)
    surprise_match = re.search(r'surprise=(-?[0-9.]+)', state_output)
    intensity_match = re.search(r'intensity=(-?[0-9.]+)', state_output)
    
    # Extract primary emotion
    primary_match = re.search(r"primary_emotion='([^']+)'", state_output)
    primary_emotion = primary_match.group(1) if primary_match else None
    
    return {
        'pleasure': float(pleasure_match.group(1)) if pleasure_match else None,
        'arousal': float(arousal_match.group(1)) if arousal_match else None,
        'dominance': float(dominance_match.group(1)) if dominance_match else None,
        'happiness': float(happiness_match.group(1)) if happiness_match else None,
        'sadness': float(sadness_match.group(1)) if sadness_match else None,
        'anger': float(anger_match.group(1)) if anger_match else None,
        'fear': float(fear_match.group(1)) if fear_match else None,
        'disgust': float(disgust_match.group(1)) if disgust_match else None,
        'surprise': float(surprise_match.group(1)) if surprise_match else None,
        'intensity': float(intensity_match.group(1)) if intensity_match else None,
        'primary_emotion': primary_emotion
    }

def print_emotional_state(state, label=""):
    """Print the emotional state values in a nice format."""
    if not state:
        print("No emotional state data available")
        return
    
    print(f"\n----- {label} EMOTIONAL STATE -----")
    
    # Print non-zero emotions first
    non_zero = []
    for key in ['pleasure', 'happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']:
        if state[key] != 0 and state[key] is not None:
            non_zero.append((key, state[key]))
    
    if non_zero:
        print("Active emotions:")
        for key, value in sorted(non_zero, key=lambda x: abs(x[1]), reverse=True):
            print(f"  {key.capitalize()}: {value:.6f}")
    else:
        print("No active emotions (all values at 0)")
    
    print(f"\nPrimary emotion: {state['primary_emotion']}")
    print(f"Intensity: {state['intensity']:.6f}")

def test_decay_rate():
    """Test the decay rate of emotions after a happy input."""
    # Get baseline emotional state
    print("=== BASELINE EMOTIONAL STATE ===")
    baseline_output = query_emotional_state()
    baseline = extract_emotional_values(baseline_output)
    print_emotional_state(baseline, "BASELINE")
    
    # Send a very intense happy message
    print("\n=== SENDING VERY INTENSE HAPPY INPUT ===")
    send_sensory_input("I am EXTREMELY happy and joyful and ecstatic today!!!", 1.0, 1.0)
    
    # Capture emotional states at different time points
    time_points = [0.5, 1, 2, 3, 4, 5]
    states = []
    
    # Wait for first time point
    time.sleep(time_points[0])
    
    # Take first measurement
    print(f"\n=== EMOTIONAL STATE AFTER {time_points[0]} SECONDS ===")
    output = query_emotional_state()
    state = extract_emotional_values(output)
    states.append(state)
    print_emotional_state(state, f"AFTER {time_points[0]} SECONDS")
    
    # For each remaining time point, wait the difference and take measurement
    for i in range(1, len(time_points)):
        wait_time = time_points[i] - time_points[i-1]
        time.sleep(wait_time)
        
        print(f"\n=== EMOTIONAL STATE AFTER {time_points[i]} SECONDS ===")
        output = query_emotional_state()
        state = extract_emotional_values(output)
        states.append(state)
        print_emotional_state(state, f"AFTER {time_points[i]} SECONDS")
    
    # Calculate and display changes over time
    print("\n=== DECAY RATE ANALYSIS ===")
    
    if baseline and all(states):
        # Track pleasure and happiness over time
        times = [0] + time_points
        happiness_values = [baseline['happiness'] or 0] + [state['happiness'] or 0 for state in states]
        pleasure_values = [baseline['pleasure'] or 0] + [state['pleasure'] or 0 for state in states]
        
        print("Happiness values over time:")
        for i, val in enumerate(happiness_values):
            print(f"  {times[i]} seconds: {val:.6f}")
        
        print("\nPleasure values over time:")
        for i, val in enumerate(pleasure_values):
            print(f"  {times[i]} seconds: {val:.6f}")
        
        # Calculate average decay rate if values are non-zero
        if any(val > 0 for val in happiness_values) and any(val > 0 for val in pleasure_values):
            # Calculate decay for happiness
            happiness_changes = []
            for i in range(len(happiness_values)-1):
                if happiness_values[i] > 0 and happiness_values[i+1] < happiness_values[i]:
                    time_diff = times[i+1] - times[i]
                    change = happiness_values[i] - happiness_values[i+1]
                    rate = change / time_diff
                    happiness_changes.append((times[i], rate))
            
            if happiness_changes:
                print("\nHappiness decay rates at each time point:")
                for time_point, rate in happiness_changes:
                    print(f"  {time_point}->{time_point+1} seconds: {rate:.6f} per second")
                
                avg_happiness_rate = sum(rate for _, rate in happiness_changes) / len(happiness_changes)
                print(f"\nAverage happiness decay rate: {avg_happiness_rate:.6f} per second")
                if avg_happiness_rate > 0:
                    print(f"At this rate, happiness would decay from 1.0 to 0 in {1.0/avg_happiness_rate:.2f} seconds")
            
            # Calculate decay for pleasure
            pleasure_changes = []
            for i in range(len(pleasure_values)-1):
                if pleasure_values[i] > 0 and pleasure_values[i+1] < pleasure_values[i]:
                    time_diff = times[i+1] - times[i]
                    change = pleasure_values[i] - pleasure_values[i+1]
                    rate = change / time_diff
                    pleasure_changes.append((times[i], rate))
            
            if pleasure_changes:
                print("\nPleasure decay rates at each time point:")
                for time_point, rate in pleasure_changes:
                    print(f"  {time_point}->{time_point+1} seconds: {rate:.6f} per second")
                
                avg_pleasure_rate = sum(rate for _, rate in pleasure_changes) / len(pleasure_changes)
                print(f"\nAverage pleasure decay rate: {avg_pleasure_rate:.6f} per second")
                if avg_pleasure_rate > 0:
                    print(f"At this rate, pleasure would decay from 1.0 to 0 in {1.0/avg_pleasure_rate:.2f} seconds")

if __name__ == "__main__":
    print("=== TESTING EMOTIONAL DECAY RATE ===")
    test_decay_rate()
    print("\nTest complete!") 