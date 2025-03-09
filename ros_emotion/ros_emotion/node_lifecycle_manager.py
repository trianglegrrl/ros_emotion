#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import subprocess
import signal
import os
import psutil
from ros_emotion.srv import NodeLifecycle
from std_msgs.msg import String

class NodeLifecycleManager(Node):
    def __init__(self):
        super().__init__('node_lifecycle_manager')
        
        # Dictionary to track managed nodes and their processes
        self.managed_nodes = {}
        
        # Create the service
        self.service = self.create_service(
            NodeLifecycle,
            'node_lifecycle_manager',
            self.handle_lifecycle_request
        )
        
        # Subscribe to node control messages as an alternative method
        self.control_subscription = self.create_subscription(
            String,
            'node_control',
            self.handle_control_message,
            10
        )
        
        # Log initialization
        self.get_logger().info("ALAINA: Node lifecycle manager initialized")
    
    def handle_lifecycle_request(self, request, response):
        """Handle service requests to start/stop nodes"""
        node_name = request.node_name
        action = request.action.lower()
        
        self.get_logger().info(f"ALAINA: Received request to {action} {node_name}")
        
        if action == "start":
            success, message = self.start_node(node_name)
        elif action == "stop":
            success, message = self.stop_node(node_name)
        else:
            success = False
            message = f"Unknown action: {action}. Must be 'start' or 'stop'."
            
        response.success = success
        response.message = message
        return response
    
    def handle_control_message(self, msg):
        """Handle control messages from a topic"""
        try:
            # Expected format: "node_name:action"
            parts = msg.data.split(":")
            if len(parts) != 2:
                self.get_logger().error(f"ALAINA: Invalid control message format: {msg.data}")
                return
                
            node_name, action = parts
            
            if action.lower() == "start":
                success, message = self.start_node(node_name)
            elif action.lower() == "stop":
                success, message = self.stop_node(node_name)
            else:
                self.get_logger().error(f"ALAINA: Unknown action in control message: {action}")
                return
                
            self.get_logger().info(f"ALAINA: Control message result: {success}, {message}")
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error processing control message: {str(e)}")
    
    def start_node(self, node_name):
        """Start a ROS node"""
        # Check if node is already running
        if node_name in self.managed_nodes and self.managed_nodes[node_name] is not None:
            if self.is_process_running(self.managed_nodes[node_name]):
                return True, f"Node {node_name} is already running"
        
        # Get path to the node script
        node_path = self.find_node_path(node_name)
        if not node_path:
            return False, f"Could not find node script for {node_name}"
        
        try:
            # Start the node
            env = os.environ.copy()
            # Ensure ROS environment is sourced
            if 'ROS_DISTRO' in env:
                self.get_logger().info(f"ALAINA: Starting {node_name} using ROS_DISTRO={env['ROS_DISTRO']}")
            
            # Start the node as a subprocess
            proc = subprocess.Popen(
                [node_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Store the process
            self.managed_nodes[node_name] = proc
            
            self.get_logger().info(f"ALAINA: Started {node_name} with PID {proc.pid}")
            return True, f"Node {node_name} started successfully"
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error starting {node_name}: {str(e)}")
            return False, f"Error starting node: {str(e)}"
    
    def stop_node(self, node_name):
        """Stop a running ROS node"""
        # Check if we're managing this node
        if node_name not in self.managed_nodes or self.managed_nodes[node_name] is None:
            # Try to find the node by name if we're not already managing it
            pid = self.find_node_by_name(node_name)
            if pid:
                self.get_logger().info(f"ALAINA: Found unmanaged node {node_name} with PID {pid}")
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    self.get_logger().info(f"ALAINA: Terminated unmanaged node {node_name}")
                    return True, f"Node {node_name} terminated successfully"
                except Exception as e:
                    self.get_logger().error(f"ALAINA: Error terminating unmanaged node {node_name}: {str(e)}")
                    return False, f"Error terminating node: {str(e)}"
            else:
                return False, f"Node {node_name} is not running or not found"
        
        # Get the process
        proc = self.managed_nodes[node_name]
        
        # Check if it's still running
        if not self.is_process_running(proc):
            self.managed_nodes[node_name] = None
            return True, f"Node {node_name} is already stopped"
        
        try:
            # Try to terminate gracefully first
            proc.terminate()
            
            # Remove from managed nodes
            self.managed_nodes[node_name] = None
            
            self.get_logger().info(f"ALAINA: Stopped {node_name}")
            return True, f"Node {node_name} stopped successfully"
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error stopping {node_name}: {str(e)}")
            return False, f"Error stopping node: {str(e)}"
    
    def is_process_running(self, proc):
        """Check if a process is still running"""
        if proc is None:
            return False
            
        try:
            # Check if process is still running
            return proc.poll() is None
        except:
            return False
    
    def find_node_path(self, node_name):
        """Find the path to a node script"""
        # This is a simplified version - in a real system you'd have a more
        # sophisticated way to find scripts, perhaps using package resources
        possible_paths = [
            os.path.join(os.path.dirname(__file__), f"{node_name}.py"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "ros_emotion", f"{node_name}.py")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # If we get here, try searching for the file
        try:
            package_dir = os.path.dirname(os.path.dirname(__file__))
            self.get_logger().info(f"ALAINA: Searching for {node_name}.py in {package_dir}")
            
            for root, _, files in os.walk(package_dir):
                if f"{node_name}.py" in files:
                    node_path = os.path.join(root, f"{node_name}.py")
                    self.get_logger().info(f"ALAINA: Found {node_name}.py at {node_path}")
                    return node_path
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error searching for node script: {str(e)}")
        
        return None
    
    def find_node_by_name(self, node_name):
        """Find a running ROS node by name and return its PID"""
        try:
            # This would need to be customized for your specific ROS setup
            # For ROS 2, you might use ros2 node list and ros2 node info
            # This is a simplified placeholder
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if node_name in proc.info['name'] or any(node_name in cmd for cmd in proc.info['cmdline']):
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.get_logger().error(f"ALAINA: Error finding node by name: {str(e)}")
        
        return None

def main(args=None):
    rclpy.init(args=args)
    node = NodeLifecycleManager()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up managed nodes on shutdown
        for node_name, proc in node.managed_nodes.items():
            if proc is not None and node.is_process_running(proc):
                node.get_logger().info(f"ALAINA: Shutting down managed node {node_name}")
                try:
                    proc.terminate()
                except:
                    pass
        
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 