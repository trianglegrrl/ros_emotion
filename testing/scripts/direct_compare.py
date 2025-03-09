#!/usr/bin/env python3

import re
import sys
import os

# Set up paths for the new directory structure
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "results")

def extract_emotional_values(filename):
    """Extract pleasure and happiness values from the emotional state output file."""
    full_path = os.path.join(RESULTS_DIR, filename)
    try:
        with open(full_path, 'r') as f:
            content = f.read()
            
        # Extract all emotional values using regex
        pleasure_match = re.search(r'pleasure=(-?[0-9.]+)', content)
        arousal_match = re.search(r'arousal=(-?[0-9.]+)', content)
        dominance_match = re.search(r'dominance=(-?[0-9.]+)', content)
        happiness_match = re.search(r'happiness=(-?[0-9.]+)', content)
        sadness_match = re.search(r'sadness=(-?[0-9.]+)', content)
        anger_match = re.search(r'anger=(-?[0-9.]+)', content)
        fear_match = re.search(r'fear=(-?[0-9.]+)', content)
        disgust_match = re.search(r'disgust=(-?[0-9.]+)', content)
        surprise_match = re.search(r'surprise=(-?[0-9.]+)', content)
        intensity_match = re.search(r'intensity=(-?[0-9.]+)', content)
        
        # Extract primary emotion
        primary_match = re.search(r"primary_emotion='([^']+)'", content)
        primary_emotion = primary_match.group(1) if primary_match else None
        
        # Extract description
        description_match = re.search(r"description='([^']+)'", content)
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
            'description': description[:100] + '...' if description and len(description) > 100 else description
        }
    except Exception as e:
        print(f"Error extracting values from {filename}: {e}")
        return None

def main():
    # Extract values from both files
    initial = extract_emotional_values('direct_initial.txt')
    updated = extract_emotional_values('direct_updated.txt')
    
    if not initial or not updated:
        print("Could not extract data from one or both files")
        return
    
    # Print basic information about both states
    print("\n===== INITIAL EMOTIONAL STATE =====")
    print(f"Pleasure: {initial['pleasure']:.6f}")
    print(f"Arousal: {initial['arousal']:.6f}")
    print(f"Dominance: {initial['dominance']:.6f}")
    print(f"Happiness: {initial['happiness']:.6f}")
    print(f"Sadness: {initial['sadness']:.6f}")
    print(f"Anger: {initial['anger']:.6f}")
    print(f"Fear: {initial['fear']:.6f}")
    print(f"Disgust: {initial['disgust']:.6f}")
    print(f"Surprise: {initial['surprise']:.6f}")
    print(f"Intensity: {initial['intensity']:.6f}")
    print(f"Primary emotion: {initial['primary_emotion']}")
    
    print("\n===== UPDATED EMOTIONAL STATE (AFTER HAPPY INPUT) =====")
    print(f"Pleasure: {updated['pleasure']:.6f}")
    print(f"Arousal: {updated['arousal']:.6f}")
    print(f"Dominance: {updated['dominance']:.6f}")
    print(f"Happiness: {updated['happiness']:.6f}")
    print(f"Sadness: {updated['sadness']:.6f}")
    print(f"Anger: {updated['anger']:.6f}")
    print(f"Fear: {updated['fear']:.6f}")
    print(f"Disgust: {updated['disgust']:.6f}")
    print(f"Surprise: {updated['surprise']:.6f}")
    print(f"Intensity: {updated['intensity']:.6f}")
    print(f"Primary emotion: {updated['primary_emotion']}")
    
    # Calculate and display changes
    print("\n===== IMMEDIATE CHANGES FROM HAPPY INPUT =====")
    
    changes = []
    for key in ['pleasure', 'arousal', 'dominance', 'happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise', 'intensity']:
        if initial[key] is not None and updated[key] is not None:
            change = updated[key] - initial[key]
            direction = '⬆️' if change > 0 else '⬇️' if change < 0 else '⟷'
            changes.append((key, change, direction))
    
    # Sort by absolute magnitude of change
    changes.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for key, change, direction in changes:
        print(f"{key.capitalize()}: {change:.6f} {direction}")
    
    # Evaluate primary changes of interest
    pleasure_change = updated['pleasure'] - initial['pleasure']
    happiness_change = updated['happiness'] - initial['happiness']
    
    print("\n===== TEST VERDICT =====")
    if pleasure_change > 0 and happiness_change > 0:
        print("✅ TEST PASSED: Happy input immediately increased both pleasure and happiness")
    elif pleasure_change > 0 or happiness_change > 0:
        print("⚠️ TEST PARTIALLY PASSED: Happy input immediately increased either pleasure or happiness, but not both")
    else:
        print("❌ TEST FAILED: Happy input did not immediately increase pleasure or happiness")
        
    if updated['primary_emotion'] != initial['primary_emotion']:
        print(f"Note: Primary emotion changed from {initial['primary_emotion']} to {updated['primary_emotion']}")

if __name__ == "__main__":
    main() 