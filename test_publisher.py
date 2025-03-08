#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

class TestPublisher(Node):
    def __init__(self):
        super().__init__('test_publisher')
        self.publisher = self.create_publisher(String, 'test_topic', 10)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.count = 0
        self.get_logger().info('ALAINA: Test publisher started')

    def timer_callback(self):
        msg = String()
        msg.data = f'Test message #{self.count}'
        self.publisher.publish(msg)
        self.get_logger().info(f'ALAINA: Publishing: {msg.data}')
        self.count += 1

def main():
    rclpy.init()
    node = TestPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 