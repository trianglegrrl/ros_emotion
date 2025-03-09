# Definition of a rumination update from the rumination engine

# Header with timestamp
builtin_interfaces/Time timestamp

# ID of the original sensory input that triggered this rumination
string original_input_id

# Current stage of rumination
uint8 rumination_stage

# Time elapsed since rumination started
builtin_interfaces/Duration elapsed_time

# Intensity of rumination (0.0 to 1.0)
float32 intensity

# Impact on emotional state (represented as changes to emotional dimensions)
float32 pleasure_change  # Change in pleasure dimension
float32 arousal_change   # Change in arousal dimension
float32 dominance_change # Change in dominance dimension

# Impact on specific emotions (represented as changes to emotion intensities)
float32 happiness_change
float32 sadness_change
float32 anger_change
float32 fear_change
float32 disgust_change
float32 surprise_change

# Human-readable description of the rumination update
string description

# Whether this is the final update for this rumination sequence
bool is_final 