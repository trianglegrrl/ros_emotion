# ROS Emotion System Testing

This project includes a comprehensive set of testing tools located in the `testing/` directory. These tools help verify that the ROS Emotion system correctly processes sensory inputs with emotional content (e.g., "happy" messages increasing pleasure and happiness).

## Quick Start

For immediate testing of happy emotional input:

```bash
# Run the optimal emotion test (tests at exactly 3 seconds after input)
./optimal_emotion_test.py
```

## Testing Directory Structure

All testing tools have been organized into a structured directory:

```
/testing/
  ├── scripts/   # Test scripts (.py, .sh)
  ├── results/   # Test result files
  └── docs/      # Documentation
```

## Key Documents

- [Emotion Testing Guide](testing/docs/emotion_testing_guide.md) - Comprehensive guide to testing the emotion system
- [Decay Rate Findings](testing/docs/decay_rate_findings.md) - Analysis of emotional decay rates
- [Emotion Test Report](testing/docs/emotion_test_report.md) - Summary of test findings

## Key Testing Scripts

The most useful tests are:

1. **Optimal Timing Test** - Tests emotional response at the optimal 3-second window:
   ```bash
   ./testing/scripts/optimal_happy_test.py
   ```

2. **Direct Happy Test** - Simple before/after test of happy input:
   ```bash
   ./testing/scripts/direct_happy_test.sh
   ```

3. **Decay Rate Analysis** - Analyzes how quickly emotions decay:
   ```bash
   ./testing/scripts/direct_decay_test.py
   ```

## Important Testing Notes

Our testing revealed several key insights:

1. There is a **processing delay** of about 2-3 seconds before emotional changes appear
2. Emotions **decay very quickly** once registered
3. The **optimal testing window** is at exactly 3 seconds after sensory input

For detailed information, please refer to the [Emotion Testing Guide](testing/docs/emotion_testing_guide.md). 