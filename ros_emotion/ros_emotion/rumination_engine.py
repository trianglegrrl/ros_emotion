#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from ros_emotion.msg import RuminationUpdate
import random
import time
import copy
import ros_emotion.utils as utils

class RuminationEngine(Node):
    def __init__(self):
        super().__init__('rumination_engine')
        
        # Load configuration
        self.config = utils.load_config(self)
        self.rumination_config = self.config.get('rumination_engine', {})
        
        # Create QoS profile
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create publishers
        self.rumination_pub = self.create_publisher(
            RuminationUpdate, 
            'rumination_update', 
            qos
        )
        
        # Create subscribers
        self.rumination_sub = self.create_subscription(
            RuminationUpdate,
            'rumination_update',
            self.rumination_callback,
            qos
        )
        
        # Active ruminations
        self.active_ruminations = {}
        
        # Configuration parameters
        self.max_active_ruminations = self.rumination_config.get('max_active_ruminations', 3)
        self.stages = self.rumination_config.get('stages', 5)
        self.update_interval = self.rumination_config.get('update_interval', 5.0)
        self.continuation_probability = self.rumination_config.get('continuation_probability', 0.8)
        self.intensity_decay = self.rumination_config.get('intensity_decay', 0.1)
        
        # Create timer for rumination updates
        update_frequency = self.rumination_config.get('update_frequency', 0.2)
        self.update_timer = self.create_timer(
            1.0 / update_frequency,
            self.update_ruminations
        )
        
        self.get_logger().info("ALAINA: Rumination Engine initialized")
    
    def rumination_callback(self, msg):
        """Process incoming rumination updates."""
        # Only process initial rumination updates (stage 0)
        if msg.rumination_stage != 0 or msg.is_final:
            return
        
        self.get_logger().info(f"ALAINA: Received initial rumination: {msg.description}")
        
        # Check if we have room for a new rumination
        if len(self.active_ruminations) >= self.max_active_ruminations:
            # Find the lowest intensity rumination to replace
            lowest_intensity = float('inf')
            lowest_id = None
            
            for rumination_id, rumination in self.active_ruminations.items():
                if rumination['update'].intensity < lowest_intensity:
                    lowest_intensity = rumination['update'].intensity
                    lowest_id = rumination_id
            
            # If the new rumination has higher intensity, replace the lowest
            if lowest_id and msg.intensity > lowest_intensity:
                self.get_logger().info(f"ALAINA: Replacing lower intensity rumination with: {msg.description}")
                self.finalize_rumination(lowest_id)
                self.active_ruminations.pop(lowest_id)
            else:
                self.get_logger().info(f"ALAINA: Ignoring rumination due to capacity: {msg.description}")
                return
        
        # Add to active ruminations
        self.active_ruminations[msg.original_input_id] = {
            'update': copy.deepcopy(msg),
            'start_time': time.time(),
            'last_update': time.time(),
            'next_stage': 1
        }
    
    def update_ruminations(self):
        """Update active ruminations."""
        current_time = time.time()
        ruminations_to_remove = []
        
        for rumination_id, rumination in self.active_ruminations.items():
            # Check if it's time for an update
            if current_time - rumination['last_update'] >= self.update_interval:
                # Update the rumination
                self.update_rumination(rumination_id, rumination, current_time)
                
                # Check if the rumination should continue
                if rumination['next_stage'] >= self.stages or random.random() > self.continuation_probability:
                    # Finalize and mark for removal
                    self.finalize_rumination(rumination_id)
                    ruminations_to_remove.append(rumination_id)
        
        # Remove finalized ruminations
        for rumination_id in ruminations_to_remove:
            self.active_ruminations.pop(rumination_id)
    
    def update_rumination(self, rumination_id, rumination, current_time):
        """Update a specific rumination."""
        # Get the current update
        current_update = rumination['update']
        
        # Create a new update
        new_update = copy.deepcopy(current_update)
        
        # Update timestamp
        new_update.timestamp = utils.get_current_time()
        
        # Update stage
        new_update.rumination_stage = rumination['next_stage']
        
        # Update elapsed time
        elapsed_seconds = current_time - rumination['start_time']
        new_update.elapsed_time = utils.create_duration(elapsed_seconds)
        
        # Update intensity (apply decay)
        new_update.intensity = max(0.0, current_update.intensity - self.intensity_decay)
        
        # Modify emotional changes based on rumination dynamics
        # In a real implementation, this would be more sophisticated
        # For now, we'll just decay the changes over time
        decay_factor = 1.0 - (rumination['next_stage'] / self.stages) * 0.5
        
        new_update.pleasure_change = current_update.pleasure_change * decay_factor
        new_update.arousal_change = current_update.arousal_change * decay_factor
        new_update.dominance_change = current_update.dominance_change * decay_factor
        
        new_update.happiness_change = current_update.happiness_change * decay_factor
        new_update.sadness_change = current_update.sadness_change * decay_factor
        new_update.anger_change = current_update.anger_change * decay_factor
        new_update.fear_change = current_update.fear_change * decay_factor
        new_update.disgust_change = current_update.disgust_change * decay_factor
        new_update.surprise_change = current_update.surprise_change * decay_factor
        
        # Update description
        new_update.description = f"Rumination stage {rumination['next_stage']}: {current_update.description}"
        
        # Not final yet
        new_update.is_final = False
        
        # Publish the update
        self.rumination_pub.publish(new_update)
        
        # Update the rumination state
        rumination['update'] = new_update
        rumination['last_update'] = current_time
        rumination['next_stage'] += 1
        
        self.get_logger().info(f"ALAINA: Updated rumination to stage {rumination['next_stage'] - 1}: {new_update.description}")
    
    def finalize_rumination(self, rumination_id):
        """Finalize a rumination by sending a final update."""
        if rumination_id not in self.active_ruminations:
            return
        
        rumination = self.active_ruminations[rumination_id]
        current_update = rumination['update']
        
        # Create a final update
        final_update = copy.deepcopy(current_update)
        
        # Update timestamp
        final_update.timestamp = utils.get_current_time()
        
        # Update elapsed time
        elapsed_seconds = time.time() - rumination['start_time']
        final_update.elapsed_time = utils.create_duration(elapsed_seconds)
        
        # Mark as final
        final_update.is_final = True
        
        # Update description
        final_update.description = f"Final rumination: {current_update.description}"
        
        # Publish the final update
        self.rumination_pub.publish(final_update)
        
        self.get_logger().info(f"ALAINA: Finalized rumination: {final_update.description}")

def main(args=None):
    rclpy.init(args=args)
    node = RuminationEngine()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("ALAINA: Keyboard interrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 