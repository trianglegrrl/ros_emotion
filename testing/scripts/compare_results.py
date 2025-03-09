#!/usr/bin/env python3

import re
import sys

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
        
        # Extract description
        description_match = re.search(r"description='([^']+)'", content)
        description = description_match.group(1) if description_match else None
        
        return {
            'pleasure': pleasure,
            'happiness': happiness,
            'primary_emotion': primary_emotion,
            'description': description[:100] + '...' if description and len(description) > 100 else description
        }
    except Exception as e:
        print(f"Error extracting values from {filename}: {e}")
        return None

def compare_values(initial, updated):
    """Compare initial and updated values."""
    if not initial or not updated:
        print("Missing data for comparison.")
        return
    
    print("\n===== COMPARISON RESULTS =====")
    
    # Pleasure comparison
    pleasure_change = updated['pleasure'] - initial['pleasure']
    print(f"Pleasure: {initial['pleasure']:.6f} → {updated['pleasure']:.6f}")
    print(f"  Change: {pleasure_change:.6f}")
    if pleasure_change > 0:
        print("  ✅ Pleasure INCREASED")
    else:
        print("  ❌ Pleasure did not increase")
    
    # Happiness comparison
    happiness_change = updated['happiness'] - initial['happiness']
    print(f"Happiness: {initial['happiness']:.6f} → {updated['happiness']:.6f}")
    print(f"  Change: {happiness_change:.6f}")
    if happiness_change > 0:
        print("  ✅ Happiness INCREASED")
    else:
        print("  ❌ Happiness did not increase")
    
    # Primary emotion comparison
    print(f"Primary emotion: {initial['primary_emotion']} → {updated['primary_emotion']}")
    
    # Overall verdict
    if pleasure_change > 0 and happiness_change > 0:
        print("\n✅ TEST PASSED: Sensory input with 'happy' increased both pleasure and happiness")
    elif pleasure_change > 0 or happiness_change > 0:
        print("\n⚠️ TEST PARTIALLY PASSED: Sensory input with 'happy' increased either pleasure or happiness, but not both")
    else:
        print("\n❌ TEST FAILED: Sensory input with 'happy' did not increase pleasure or happiness")

def main():
    initial_values = extract_emotional_values('initial_state.txt')
    updated_values = extract_emotional_values('updated_state.txt')
    
    print("===== INITIAL STATE =====")
    print(f"Pleasure: {initial_values['pleasure']}")
    print(f"Happiness: {initial_values['happiness']}")
    print(f"Primary emotion: {initial_values['primary_emotion']}")
    print(f"Description: {initial_values['description']}")

    print("\n===== UPDATED STATE =====")
    print(f"Pleasure: {updated_values['pleasure']}")
    print(f"Happiness: {updated_values['happiness']}")
    print(f"Primary emotion: {updated_values['primary_emotion']}")
    print(f"Description: {updated_values['description']}")
    
    compare_values(initial_values, updated_values)

if __name__ == "__main__":
    main() 