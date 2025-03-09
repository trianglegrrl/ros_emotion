#!/usr/bin/env python3

import subprocess
import json
import time
import sys
import re
import os

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
    cmd = f"ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{{input_type: \"text\", description: \"{escaped_message}\", source: \"emotions_test\", intensity: {intensity}, priority: {priority}}}'"
    
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
    
    # Extract description
    description_match = re.search(r"description='([^']+)'", state_output)
    description = description_match.group(1) if description_match else None
    
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
        'primary_emotion': primary_emotion,
        'description': description
    }

def print_emotional_state(state, label=""):
    """Print the emotional state in a nice format."""
    if not state:
        print("No emotional state data available")
        return
    
    print(f"\n----- {label} EMOTIONAL STATE -----")
    print(f"Primary emotion: {state['primary_emotion']}")
    print("\nPAD Model:")
    print(f"  Pleasure: {state['pleasure']:.6f}")
    print(f"  Arousal: {state['arousal']:.6f}")
    print(f"  Dominance: {state['dominance']:.6f}")
    
    print("\nBasic Emotions:")
    print(f"  Happiness: {state['happiness']:.6f}")
    print(f"  Sadness: {state['sadness']:.6f}")
    print(f"  Anger: {state['anger']:.6f}")
    print(f"  Fear: {state['fear']:.6f}")
    print(f"  Disgust: {state['disgust']:.6f}")
    print(f"  Surprise: {state['surprise']:.6f}")
    
    print(f"\nIntensity: {state['intensity']:.6f}")

def calculate_changes(before, after):
    """Calculate and display changes between two emotional states."""
    if not before or not after:
        print("Missing data for comparison")
        return
    
    changes = []
    for key in ['pleasure', 'arousal', 'dominance', 'happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise', 'intensity']:
        if before[key] is not None and after[key] is not None:
            change = after[key] - before[key]
            direction = '↑' if change > 0 else '↓' if change < 0 else '-'
            changes.append((key, change, direction))
    
    # Sort by absolute magnitude of change
    changes.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for key, change, direction in changes:
        sign = '+' if change > 0 else ''
        print(f"  {key.capitalize()}: {sign}{change:.6f} {direction}")
    
    return changes

def test_immediate_effect():
    """Test the immediate effect of happy input."""
    # Get current emotional state before input
    print("Querying current emotional state...")
    before_output = query_emotional_state()
    before = extract_emotional_values(before_output)
    
    if not before:
        print("Error: Could not get current emotional state")
        return
    
    print_emotional_state(before, "BEFORE")
    
    # Send happy input
    print("\nSending happy sensory input...")
    happy_message = "I am extremely happy and joyful today!"
    send_sensory_input(happy_message, 1.0, 1.0)
    
    # Wait minimally
    print("Waiting 1 second for processing...")
    time.sleep(1)
    
    # Get state immediately after input
    print("Querying emotional state after happy input...")
    after_output = query_emotional_state()
    after = extract_emotional_values(after_output)
    
    if not after:
        print("Error: Could not get updated emotional state")
        return
    
    print_emotional_state(after, "AFTER HAPPY INPUT")
    
    # Calculate and display changes
    print("\n===== IMMEDIATE CHANGES FROM HAPPY INPUT =====")
    changes = calculate_changes(before, after)
    
    # Evaluate results
    print("\n===== TEST VERDICT =====")
    pleasure_change = after['pleasure'] - before['pleasure']
    happiness_change = after['happiness'] - before['happiness']
    
    if pleasure_change > 0 and happiness_change > 0:
        print("✅ TEST PASSED: Happy input immediately increased both pleasure and happiness")
    elif pleasure_change > 0 or happiness_change > 0:
        print("⚠️ TEST PARTIALLY PASSED: Happy input immediately increased either pleasure or happiness, but not both")
    else:
        print("❌ TEST FAILED: Happy input did not immediately increase pleasure or happiness")
    
    return before, after, changes

if __name__ == "__main__":
    print("=== TESTING IMMEDIATE EFFECT OF HAPPY INPUT ===")
    before, after, changes = test_immediate_effect()
    print("\nTest complete!") 