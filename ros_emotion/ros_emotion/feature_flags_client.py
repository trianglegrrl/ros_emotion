#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from ros_emotion.srv import FeatureFlags
from functools import lru_cache
import time

class FeatureFlagsClient:
    """Client for the feature flags service."""
    
    def __init__(self, node):
        """Initialize the client.
        
        Args:
            node: The ROS node that will use this client.
        """
        self.node = node
        self.client = node.create_client(FeatureFlags, 'feature_flags')
        self.cache = {}
        self.cache_timeout = 10.0  # Cache values for 10 seconds (increased from 5)
        self.last_cache_update = 0.0
        self.service_timeout = 3.0  # Increase service timeout to 3 seconds (up from 0.5)
        
        # Wait for the service to be available
        timeout = 10.0  # Increase initial wait timeout to 10 seconds
        if not self.client.wait_for_service(timeout_sec=timeout):
            node.get_logger().warn(f"ALAINA: Feature flags service not available after waiting {timeout} seconds. Will try to continue anyway.")
        else:
            node.get_logger().info("ALAINA: Feature flags service is available.")
        
    def refresh_cache(self):
        """Refresh the cache of feature flags."""
        # Skip if cache is still fresh
        if time.time() - self.last_cache_update < self.cache_timeout:
            return True
            
        # Skip if service is not available
        if not self.client.service_is_ready():
            self.node.get_logger().debug("ALAINA: Feature flags service not ready for refresh_cache call")
            return False
        
        request = FeatureFlags.Request()
        request.operation = "list"
        
        try:
            future = self.client.call_async(request)
            
            # Use a longer timeout to avoid blocking
            end_time = time.time() + self.service_timeout
            while not future.done() and time.time() < end_time:
                rclpy.spin_once(self.node, timeout_sec=0.1)
                
            if future.done():
                response = future.result()
                if response.success:
                    # Update cache
                    self.cache = {}
                    for i, name in enumerate(response.feature_names):
                        value = response.feature_values[i].lower() == 'true'
                        self.cache[name] = value
                    self.last_cache_update = time.time()
                    return True
                else:
                    self.node.get_logger().error(f"ALAINA: Error refreshing feature flags: {response.error_message}")
            else:
                self.node.get_logger().warn("ALAINA: Feature flags service call timed out for refresh_cache")
        except Exception as e:
            self.node.get_logger().error(f"ALAINA: Error refreshing feature flags cache: {str(e)}")
        
        return False
    
    def is_feature_enabled(self, feature_name, default=True):
        """Check if a feature is enabled.
        
        Args:
            feature_name: The name of the feature to check.
            default: The default value to return if the feature doesn't exist or service fails.
            
        Returns:
            bool: True if the feature is enabled, False otherwise.
        """
        # Try to refresh the cache if it's stale
        refresh_success = self.refresh_cache()
        
        # Check cache first (even if refresh failed, we might have old values)
        if feature_name in self.cache:
            return self.cache[feature_name]
        
        # If cache refresh failed but we didn't have the feature in cache, 
        # or if the feature is not in cache after a successful refresh, 
        # make a direct request if the service is ready
        if self.client.service_is_ready():
            request = FeatureFlags.Request()
            request.operation = "get"
            request.feature_name = feature_name
            
            try:
                future = self.client.call_async(request)
                
                # Use a longer timeout to avoid blocking
                end_time = time.time() + self.service_timeout
                while not future.done() and time.time() < end_time:
                    rclpy.spin_once(self.node, timeout_sec=0.1)
                    
                if future.done():
                    response = future.result()
                    if response.success and response.feature_values:
                        value = response.feature_values[0].lower() == 'true'
                        # Update cache
                        self.cache[feature_name] = value
                        self.last_cache_update = time.time()
                        return value
                else:
                    self.node.get_logger().warn(f"ALAINA: Feature flags service call for '{feature_name}' timed out")
            except Exception as e:
                self.node.get_logger().error(f"ALAINA: Error checking feature flag '{feature_name}': {str(e)}")
        else:
            self.node.get_logger().debug(f"ALAINA: Feature flags service not ready for is_feature_enabled({feature_name}) call")
        
        self.node.get_logger().debug(f"ALAINA: Using default value ({default}) for feature '{feature_name}'")
        return default
    
    def set_feature(self, feature_name, value):
        """Set a feature flag value.
        
        Args:
            feature_name: The name of the feature to set.
            value: The new value for the feature (boolean).
            
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        if not self.client.service_is_ready():
            self.node.get_logger().warn(f"ALAINA: Feature flags service not ready for set_feature call")
            return False
            
        request = FeatureFlags.Request()
        request.operation = "set"
        request.feature_name = feature_name
        request.value = str(value).lower()
        
        try:
            future = self.client.call_async(request)
            
            # Wait for response with timeout
            end_time = time.time() + self.service_timeout
            while not future.done() and time.time() < end_time:
                rclpy.spin_once(self.node, timeout_sec=0.1)
                
            if future.done():
                response = future.result()
                if response.success:
                    # Update cache
                    if response.feature_values:
                        self.cache[feature_name] = response.feature_values[0].lower() == 'true'
                        self.last_cache_update = time.time()
                    return True
            else:
                self.node.get_logger().warn(f"ALAINA: Setting feature flag '{feature_name}' timed out")
        except Exception as e:
            self.node.get_logger().error(f"ALAINA: Error setting feature flag '{feature_name}': {str(e)}")
        
        return False
    
    def get_all_features(self):
        """Get all feature flags.
        
        Returns:
            dict: A dictionary of feature flags, each with name, value, and description.
        """
        if not self.client.service_is_ready():
            self.node.get_logger().warn(f"ALAINA: Feature flags service not ready for get_all_features call")
            return []
            
        request = FeatureFlags.Request()
        request.operation = "list"
        
        try:
            future = self.client.call_async(request)
            
            # Wait for response with timeout
            end_time = time.time() + self.service_timeout
            while not future.done() and time.time() < end_time:
                rclpy.spin_once(self.node, timeout_sec=0.1)
                
            if future.done():
                response = future.result()
                if response.success:
                    features = []
                    for i, name in enumerate(response.feature_names):
                        features.append({
                            'name': name,
                            'value': response.feature_values[i].lower() == 'true',
                            'description': response.feature_descriptions[i]
                        })
                    # Update cache
                    for feature in features:
                        self.cache[feature['name']] = feature['value']
                    self.last_cache_update = time.time()
                    return features
            else:
                self.node.get_logger().warn("ALAINA: Getting all feature flags timed out")
        except Exception as e:
            self.node.get_logger().error(f"ALAINA: Error getting all feature flags: {str(e)}")
        
        return [] 