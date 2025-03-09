#!/usr/bin/env python3

import subprocess
import json
import time
import sys
import re
import os

# Dictionary of test messages for different emotions
TEST_MESSAGES = {
    "happy": "I am extremely happy and joyful today!",
    "sad": "That makes me feel so sad and disappointed.",
    "angry": "I am very angry about what happened.",
    "fearful": "That is terrifying and makes me very afraid.",
    "disgusted": "That is utterly disgusting and repulsive.",
    "surprised": "Wow! That was a huge surprise!"
}

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

def test_emotions():
    """Run emotional tests for all emotion types."""
    results = {}
    
    # Reset with neutral message
    print("Sending neutral message to reset emotional state...")
    send_sensory_input("This is a neutral message", 0.5, 0.5)
    time.sleep(2)
    
    # Get baseline state
    print("\n=== Baseline Emotional State ===")
    baseline_output = query_emotional_state()
    baseline = extract_emotional_values(baseline_output)
    results["baseline"] = baseline
    
    if not baseline:
        print("Error: Could not get baseline emotional state")
        return
    
    print_emotional_state(baseline, "BASELINE")
    
    # Test each emotion
    for emotion, message in TEST_MESSAGES.items():
        print(f"\n=== Testing {emotion.upper()} input ===")
        
        # Send the emotional input
        print(f"Sending message: \"{message}\"")
        send_sensory_input(message)
        
        # Wait minimally for processing
        time.sleep(1)
        
        # Get updated state
        state_output = query_emotional_state()
        state = extract_emotional_values(state_output)
        results[emotion] = state
        
        if not state:
            print(f"Error: Could not get {emotion} emotional state")
            continue
        
        print_emotional_state(state, emotion.upper())
        
        # Calculate and display changes from baseline
        print("\nChanges from baseline:")
        calculate_changes(baseline, state)
        
        # Wait before next test to allow decay
        time.sleep(3)
    
    # Summarize results
    print("\n=== SUMMARY OF EMOTIONAL RESPONSES ===")
    for emotion in TEST_MESSAGES.keys():
        if emotion in results and results[emotion]:
            primary = results[emotion]['primary_emotion']
            print(f"{emotion.capitalize()} input → Primary emotion: {primary}")
            
            # Show the emotion that changed the most
            changes = {}
            for key in ['happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']:
                if baseline[key] is not None and results[emotion][key] is not None:
                    changes[key] = results[emotion][key] - baseline[key]
            
            # Find emotion with biggest change
            if changes:
                max_change = max(changes.items(), key=lambda x: abs(x[1]))
                sign = '+' if max_change[1] > 0 else ''
                print(f"  Biggest change: {max_change[0]} ({sign}{max_change[1]:.6f})")
    
    return results

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

def calculate_changes(initial, updated):
    """Calculate and display changes between two emotional states."""
    if not initial or not updated:
        print("Missing data for comparison")
        return
    
    changes = []
    for key in ['pleasure', 'arousal', 'dominance', 'happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise', 'intensity']:
        if initial[key] is not None and updated[key] is not None:
            change = updated[key] - initial[key]
            changes.append((key, change))
    
    # Sort by absolute magnitude of change
    changes.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for key, change in changes:
        direction = '↑' if change > 0 else '↓' if change < 0 else '-'
        print(f"  {key.capitalize()}: {change:.6f} {direction}")

if __name__ == "__main__":
    print("=== TESTING EMOTIONAL RESPONSES TO DIFFERENT INPUTS ===")
    results = test_emotions()
    print("\nTest complete!") 