# Definition of emotional response to sensory inputs or rumination

# Header with timestamp
builtin_interfaces/Time timestamp

# ID to correlate with original stimulus
string stimulus_id

# Is this a response to rumination
bool is_rumination

# Response text
string response_text  

# Source of the response (e.g., "llm", "rule_based", "manual")
string source

# Emotional state before this response (if applicable)
EmotionalState previous_state

# Emotional state after this response
EmotionalState new_state

# Changes applied to the emotional state
float32 pleasure_delta
float32 arousal_delta
float32 dominance_delta

# Primary emotion affected by this response
string primary_emotion

# Intensity of the response (0.0 to 1.0)
float32 intensity

# Confidence in the response (0.0 to 1.0)
float32 confidence

# Optional metadata as JSON string
string metadata 