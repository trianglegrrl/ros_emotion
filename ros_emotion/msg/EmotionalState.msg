# Definition of the emotional state using a dimensional model (PAD - Pleasure, Arousal, Dominance)
# along with basic emotion categories based on psychological models

# Header with timestamp
builtin_interfaces/Time timestamp

# Dimensional model values (PAD model)
float32 pleasure  # -1.0 to 1.0 (negative to positive)
float32 arousal   # -1.0 to 1.0 (calm to excited)
float32 dominance # -1.0 to 1.0 (submissive to dominant)

# Basic emotion categories with intensity values (0.0 to 1.0)
float32 happiness
float32 sadness
float32 anger
float32 fear
float32 disgust
float32 surprise

# Overall emotional intensity
float32 intensity

# Confidence in emotional assessment
float32 confidence

# Source of this emotional state update
string source

# Optional human-readable description of the emotional state
string description

# Primary dominant emotion (e.g., "happiness", "sadness", "anger", "fear", "disgust", "surprise")
string primary_emotion 