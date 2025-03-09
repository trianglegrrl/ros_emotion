# ROS Emotion Testing Suite

This directory contains tools and documentation for testing the ROS Emotion system's response to sensory inputs.

## Directory Structure

- `scripts/`: Test scripts (Python and Shell)
- `results/`: Test output files
- `docs/`: Testing documentation and findings

## Key Documents

- [Emotion Testing Guide](docs/emotion_testing_guide.md): Comprehensive guide to testing the emotion system
- [Decay Rate Findings](docs/decay_rate_findings.md): Analysis of emotional decay rates
- [Emotion Test Report](docs/emotion_test_report.md): Summary of test findings

## Running Tests

To run a test, use the scripts in the `scripts/` directory. For example:

```bash
# Test with optimal timing
./scripts/optimal_happy_test.py

# Test with multiple inputs
./scripts/multi_happy_test.sh
```

See the [Emotion Testing Guide](docs/emotion_testing_guide.md) for detailed information on the available tests and best practices.
