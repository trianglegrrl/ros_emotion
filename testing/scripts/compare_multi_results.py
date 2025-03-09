#!/usr/bin/env python3

import re
import sys
import os

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
    
    # Print a simple ASCII chart for visualization
    print("\n===== PLEASURE CHART =====")
    max_pleasure = max([state['pleasure'] for state in states])
    for i, state in enumerate(states):
        bar_length = int((state['pleasure'] / max_pleasure) * 40) if max_pleasure > 0 else 0
        print(f"Input {i}: {'█' * bar_length} {state['pleasure']:.6f}")
    
    print("\n===== HAPPINESS CHART =====")
    max_happiness = max([state['happiness'] for state in states])
    for i, state in enumerate(states):
        bar_length = int((state['happiness'] / max_happiness) * 40) if max_happiness > 0 else 0
        print(f"Input {i}: {'█' * bar_length} {state['happiness']:.6f}")
    
    # Determine if test passed
    if overall_pleasure > 0 and overall_happiness > 0:
        print("\n✅ TEST PASSED: Multiple happy inputs increased both pleasure and happiness")
    elif overall_pleasure > 0 or overall_happiness > 0:
        print("\n⚠️ TEST PARTIALLY PASSED: Multiple happy inputs increased either pleasure or happiness, but not both")
    else:
        print("\n❌ TEST FAILED: Multiple happy inputs did not increase pleasure or happiness")

if __name__ == "__main__":
    main()
