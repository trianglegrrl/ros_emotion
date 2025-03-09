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
    
    # Print all emotions
    emotions = [
        ('pleasure', state['pleasure'] or 0),
        ('happiness', state['happiness'] or 0),
        ('sadness', state['sadness'] or 0),
        ('anger', state['anger'] or 0),
        ('fear', state['fear'] or 0),
        ('disgust', state['disgust'] or 0),
        ('surprise', state['surprise'] or 0)
    ]
    
    # Sort by absolute value, largest first
    emotions.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for name, value in emotions:
        print(f"  {name.capitalize()}: {value:.6f}")
    
    print(f"\nPrimary emotion: {state['primary_emotion']}")
    print(f"Intensity: {state['intensity']:.6f}")

def test_happy_input_optimal_timing():
    """Test the effect of happy input at the optimal time window (3 seconds)."""
    # Get baseline emotional state
    print("=== BASELINE EMOTIONAL STATE ===")
    baseline_output = query_emotional_state()
    baseline = extract_emotional_values(baseline_output)
    print_emotional_state(baseline, "BASELINE")
    
    # Define test cases with different content
    test_cases = [
        {
            "name": "HAPPY INPUT",
            "message": "I am extremely happy and joyful today!",
            "intensity": 1.0,
            "priority": 1.0
        },
        {
            "name": "NEUTRAL INPUT",
            "message": "This is a neutral message with no emotional content.",
            "intensity": 1.0,
            "priority": 1.0
        }
    ]
    
    results = {}
    
    # Run each test case with optimal timing
    for test in test_cases:
        print(f"\n=== TESTING {test['name']} ===")
        
        # Send input
        print(f"Sending message: \"{test['message']}\"")
        send_sensory_input(test['message'], test['intensity'], test['priority'])
        
        # Wait exactly 3 seconds (optimal time window based on our research)
        print("Waiting exactly 3 seconds for optimal measurement...")
        time.sleep(3)
        
        # Query emotional state at exactly 3 seconds
        print(f"Querying emotional state at 3-second mark...")
        output = query_emotional_state()
        state = extract_emotional_values(output)
        print_emotional_state(state, f"{test['name']} RESULT (3 seconds)")
        
        # Store the result
        results[test['name']] = state
        
        # Wait for emotions to fully decay before next test
        print("Waiting 10 seconds for emotions to decay before next test...")
        time.sleep(10)
    
    # Compare results
    print("\n=== COMPARISON OF RESULTS ===")
    
    happy_result = results["HAPPY INPUT"]
    neutral_result = results["NEUTRAL INPUT"]
    
    print("\nDifference between HAPPY and NEUTRAL inputs:")
    
    emotion_diffs = []
    for emotion in ['pleasure', 'happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise']:
        happy_val = happy_result[emotion] or 0
        neutral_val = neutral_result[emotion] or 0
        diff = happy_val - neutral_val
        emotion_diffs.append((emotion, diff))
    
    # Sort by absolute difference
    emotion_diffs.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for emotion, diff in emotion_diffs:
        direction = "↑" if diff > 0 else "↓" if diff < 0 else "-"
        print(f"  {emotion.capitalize()}: {diff:.6f} {direction}")
    
    # Overall verdict
    happiness_diff = (happy_result['happiness'] or 0) - (neutral_result['happiness'] or 0)
    pleasure_diff = (happy_result['pleasure'] or 0) - (neutral_result['pleasure'] or 0)
    
    print("\n=== TEST VERDICT ===")
    if happiness_diff > 0 and pleasure_diff > 0:
        print("✅ TEST PASSED: Happy input increases both pleasure and happiness compared to neutral input")
    elif happiness_diff > 0 or pleasure_diff > 0:
        print("⚠️ TEST PARTIALLY PASSED: Happy input increases either pleasure or happiness, but not both")
    else:
        print("❌ TEST FAILED: Happy input does not increase pleasure or happiness compared to neutral input")

if __name__ == "__main__":
    print("=== TESTING HAPPY INPUT AT OPTIMAL TIMING ===")
    test_happy_input_optimal_timing()
    print("\nTest complete!") 