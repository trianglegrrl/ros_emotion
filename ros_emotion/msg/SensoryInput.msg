# Definition of sensory input for the emotion system

# Header with timestamp
builtin_interfaces/Time timestamp

# Type of sensory input
string input_type  # e.g., "visual", "auditory", "text", "touch", "combined"

# Natural language description of the sensory input
string description

# Raw sensor data (if applicable)
string raw_data

# Source of the sensory input
string source

# Intensity of the sensory input (0.0 to 1.0)
float32 intensity

# Priority of the sensory input (0.0 to 1.0)
float32 priority

# Confidence in the sensory input (0.0 to 1.0)
float32 confidence

# Optional metadata as JSON string
string metadata 