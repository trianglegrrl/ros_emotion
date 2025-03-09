#!/bin/bash

echo "=== Testing Multiple Happy Sensory Inputs ==="

# First, check the current emotional state
echo "Querying initial emotional state..."
docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'" > multi_test_state_0.txt

echo "Initial state saved to multi_test_state_0.txt"

# Loop to send 5 happy sensory inputs
for i in {1..5}
do
    echo "Sending happy sensory input #$i..."
    
    # Vary the happy messages slightly
    case $i in
        1) message="I feel very happy and content today" ;;
        2) message="Today is such a happy day with beautiful sunshine" ;;
        3) message="I'm so happy with these wonderful results" ;;
        4) message="Meeting with friends made me really happy" ;;
        5) message="The happy celebration was a great success" ;;
    esac
    
    # Send the input
    docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 topic pub --once /sensory_input ros_emotion/msg/SensoryInput '{input_type: \"text\", description: \"$message\", source: \"test_script\", intensity: 0.7, priority: 0.6}'"
    
    # Wait for processing
    echo "Waiting 5 seconds for processing..."
    sleep 5
    
    # Query and save the updated state
    echo "Querying emotional state after input #$i..."
    docker exec -it ros_emotion_container bash -c "source /opt/ros/foxy/setup.bash && source /ros_ws/install/setup.bash && ros2 service call /query_emotional_state ros_emotion/srv/EmotionQuery '{query_type: \"full\", specific_emotion: \"\", include_description: true}'" > "multi_test_state_$i.txt"
    
    echo "State after input #$i saved to multi_test_state_$i.txt"
done

echo "=== Test Complete ==="
echo "Running comparison analysis..."

# Create a Python script to compare all states
cat > compare_multi_results.py << 'EOF'
#!/usr/bin/env python3

import re
import sys
import os
import matplotlib.pyplot as plt

def extract_emotional_values(filename):
    """Extract pleasure and happiness values from the emotional state output file."""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            
        # Extract pleasure value using regex
        pleasure_match = re.search(r'pleasure=(-?[0-9.]+)', content)
        pleasure = float(pleasure_match.group(1)) if pleasure_match else None
        
        # Extract happiness value using regex
        happiness_match = re.search(r'happiness=(-?[0-9.]+)', content)
        happiness = float(happiness_match.group(1)) if happiness_match else None
        
        # Extract primary emotion
        primary_match = re.search(r"primary_emotion='([^']+)'", content)
        primary_emotion = primary_match.group(1) if primary_match else None
        
        # Extract intensity
        intensity_match = re.search(r'intensity=(-?[0-9.]+)', content)
        intensity = float(intensity_match.group(1)) if intensity_match else None
        
        return {
            'pleasure': pleasure,
            'happiness': happiness,
            'primary_emotion': primary_emotion,
            'intensity': intensity
        }
    except Exception as e:
        print(f"Error extracting values from {filename}: {e}")
        return None

def main():
    # Collect data from each state file
    states = []
    for i in range(6):  # 0 through 5
        filename = f'multi_test_state_{i}.txt'
        if os.path.exists(filename):
            values = extract_emotional_values(filename)
            if values:
                states.append(values)
                print(f"State {i}: Pleasure={values['pleasure']:.6f}, Happiness={values['happiness']:.6f}, Emotion={values['primary_emotion']}")
    
    if len(states) < 2:
        print("Not enough data for comparison")
        return
    
    # Calculate changes
    print("\n===== CHANGES BETWEEN STATES =====")
    for i in range(1, len(states)):
        pleasure_change = states[i]['pleasure'] - states[i-1]['pleasure']
        happiness_change = states[i]['happiness'] - states[i-1]['happiness']
        
        print(f"Change after input #{i}:")
        print(f"  Pleasure: {pleasure_change:.6f} {'⬆️' if pleasure_change > 0 else '⬇️' if pleasure_change < 0 else '⟷'}")
        print(f"  Happiness: {happiness_change:.6f} {'⬆️' if happiness_change > 0 else '⬇️' if happiness_change < 0 else '⟷'}")
    
    # Calculate overall change
    overall_pleasure = states[-1]['pleasure'] - states[0]['pleasure']
    overall_happiness = states[-1]['happiness'] - states[0]['happiness']
    
    print("\n===== OVERALL CHANGES =====")
    print(f"Pleasure: {states[0]['pleasure']:.6f} → {states[-1]['pleasure']:.6f}")
    print(f"  Total change: {overall_pleasure:.6f}")
    print(f"Happiness: {states[0]['happiness']:.6f} → {states[-1]['happiness']:.6f}")
    print(f"  Total change: {overall_happiness:.6f}")
    
    # Determine if test passed
    if overall_pleasure > 0 and overall_happiness > 0:
        print("\n✅ TEST PASSED: Multiple happy inputs increased both pleasure and happiness")
    elif overall_pleasure > 0 or overall_happiness > 0:
        print("\n⚠️ TEST PARTIALLY PASSED: Multiple happy inputs increased either pleasure or happiness, but not both")
    else:
        print("\n❌ TEST FAILED: Multiple happy inputs did not increase pleasure or happiness")
        
    # Create graphs if matplotlib is available
    try:
        # Prepare data
        x = list(range(len(states)))
        pleasure_values = [state['pleasure'] for state in states]
        happiness_values = [state['happiness'] for state in states]
        intensity_values = [state['intensity'] for state in states]
        
        # Create figure with multiple subplots
        plt.figure(figsize=(10, 6))
        
        # Pleasure plot
        plt.subplot(3, 1, 1)
        plt.plot(x, pleasure_values, 'r-o', label='Pleasure')
        plt.title('Pleasure Change with Happy Inputs')
        plt.ylabel('Pleasure Value')
        plt.grid(True)
        
        # Happiness plot
        plt.subplot(3, 1, 2)
        plt.plot(x, happiness_values, 'g-o', label='Happiness')
        plt.title('Happiness Change with Happy Inputs')
        plt.ylabel('Happiness Value')
        plt.grid(True)
        
        # Intensity plot
        plt.subplot(3, 1, 3)
        plt.plot(x, intensity_values, 'b-o', label='Intensity')
        plt.title('Emotional Intensity with Happy Inputs')
        plt.xlabel('Input Number (0 = baseline)')
        plt.ylabel('Intensity Value')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('happy_test_results.png')
        print("\nGraph saved to happy_test_results.png")
    except Exception as e:
        print(f"\nCould not create graphs: {e}")

if __name__ == "__main__":
    main()
EOF

# Make the comparison script executable
chmod +x compare_multi_results.py

# Run the comparison
python3 compare_multi_results.py

echo "Test summary complete!" 