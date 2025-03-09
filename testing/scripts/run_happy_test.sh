#!/bin/bash

# Make the Python script executable
chmod +x test_happy_input.py

# Run the test
python3 test_happy_input.py

# Print the exit status
exit_code=$?
if [ $exit_code -eq 0 ]; then
  echo "Test completed successfully!"
else
  echo "Test completed with warnings or errors."
fi

exit $exit_code 