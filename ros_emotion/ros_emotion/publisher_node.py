#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

class EmotionPublisher(Node):
    def __init__(self):
        super().__init__('emotion_publisher')
        self.publisher_ = self.create_publisher(String, 'emotion', 10)
        self.timer = self.create_timer(5.0, self.timer_callback)
        self.get_logger().info('ALAINA: Emotion publisher has been started')

    def timer_callback(self):
        msg = String()
        msg.data = 'Hello World!'
        self.publisher_.publish(msg)
        self.get_logger().info('ALAINA: Publishing: "%s"' % msg.data)

def main(args=None):
    rclpy.init(args=args)
    publisher = EmotionPublisher()
    try:
        rclpy.spin(publisher)
    except KeyboardInterrupt:
        publisher.get_logger().info('ALAINA: Keyboard interrupt, shutting down')
    finally:
        publisher.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 