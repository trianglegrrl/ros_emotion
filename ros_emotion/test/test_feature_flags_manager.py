#!/usr/bin/env python3

import unittest
import time
import rclpy
from rclpy.node import Node
from ros_emotion.srv import FeatureFlags
from ros_emotion.feature_flags_manager import FeatureFlagsManager

class TestFeatureFlagsClient(Node):
    """Client to test the feature flags service."""
    
    def __init__(self):
        super().__init__('test_feature_flags_client')
        self.client = self.create_client(FeatureFlags, 'feature_flags')
        
    def wait_for_service(self, timeout_sec=5.0):
        """Wait for the service to be available."""
        return self.client.wait_for_service(timeout_sec=timeout_sec)
        
    def list_features(self):
        """List all feature flags."""
        request = FeatureFlags.Request()
        request.operation = 'list'
        
        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)
        return future.result()
        
    def get_feature(self, feature_name):
        """Get the value of a feature flag."""
        request = FeatureFlags.Request()
        request.operation = 'get'
        request.feature_name = feature_name
        
        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)
        return future.result()
        
    def set_feature(self, feature_name, value):
        """Set the value of a feature flag."""
        request = FeatureFlags.Request()
        request.operation = 'set'
        request.feature_name = feature_name
        request.value = str(value).lower()
        
        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)
        return future.result()

class TestFeatureFlagsManager(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialize ROS
        rclpy.init()
        
        # Create the feature flags manager node
        cls.manager_node = FeatureFlagsManager()
        cls.executor = rclpy.executors.SingleThreadedExecutor()
        cls.executor.add_node(cls.manager_node)
        
        # Start spinning in a separate thread
        cls.spin_thread = threading.Thread(target=cls.executor.spin)
        cls.spin_thread.daemon = True
        cls.spin_thread.start()
        
        # Create a test client
        cls.client_node = TestFeatureFlagsClient()
        
        # Wait for the service to be available
        timeout = 5.0
        if not cls.client_node.wait_for_service(timeout_sec=timeout):
            cls.tearDownClass()
            raise RuntimeError(f'Service not available within timeout of {timeout} seconds')
    
    @classmethod
    def tearDownClass(cls):
        # Clean up
        cls.executor.shutdown()
        cls.manager_node.destroy_node()
        cls.client_node.destroy_node()
        rclpy.shutdown()
    
    def test_list_features(self):
        """Test listing feature flags."""
        response = self.client_node.list_features()
        
        # Verify response
        self.assertTrue(response.success)
        self.assertGreater(len(response.feature_names), 0)
        self.assertEqual(len(response.feature_names), len(response.feature_values))
        self.assertEqual(len(response.feature_names), len(response.feature_descriptions))
        
        # Check for the rumination_enabled flag
        self.assertIn('rumination_enabled', response.feature_names)
    
    def test_get_feature(self):
        """Test getting a feature flag."""
        response = self.client_node.get_feature('rumination_enabled')
        
        # Verify response
        self.assertTrue(response.success)
        self.assertEqual(len(response.feature_names), 1)
        self.assertEqual(response.feature_names[0], 'rumination_enabled')
        self.assertIn(response.feature_values[0], ['true', 'false'])
    
    def test_set_feature(self):
        """Test setting a feature flag."""
        # Get the current value
        get_response = self.client_node.get_feature('rumination_enabled')
        original_value = get_response.feature_values[0] == 'true'
        
        # Set the opposite value
        new_value = not original_value
        set_response = self.client_node.set_feature('rumination_enabled', new_value)
        
        # Verify set response
        self.assertTrue(set_response.success)
        
        # Get the new value to verify it was set
        get_response = self.client_node.get_feature('rumination_enabled')
        updated_value = get_response.feature_values[0] == 'true'
        
        # Verify the value was changed
        self.assertEqual(updated_value, new_value)
        
        # Set back to original value
        self.client_node.set_feature('rumination_enabled', original_value)
    
    def test_invalid_operation(self):
        """Test with an invalid operation."""
        request = FeatureFlags.Request()
        request.operation = 'invalid_operation'
        
        future = self.client_node.client.call_async(request)
        rclpy.spin_until_future_complete(self.client_node, future, timeout_sec=1.0)
        response = future.result()
        
        # Verify response
        self.assertFalse(response.success)
        self.assertIn("Invalid operation", response.error_message)
    
    def test_nonexistent_feature(self):
        """Test getting a nonexistent feature flag."""
        response = self.client_node.get_feature('nonexistent_feature')
        
        # Verify response
        self.assertFalse(response.success)
        self.assertIn("not found", response.error_message)

if __name__ == '__main__':
    import threading
    unittest.main() 