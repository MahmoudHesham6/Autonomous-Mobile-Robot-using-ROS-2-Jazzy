import math
import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

# Map-frame coordinates (x, y, yaw in radians). Adjust to free spots on your map.
STATIONS = {
    'pickup':  (2.5, -1.5, 0.0),
    'dropoff': (-2.5, 1.5, math.pi),
    'home':    (0.0, 0.0, 0.0),
}


def make_pose(nav, x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = nav.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def go_to(nav, name):
    nav.get_logger().info(f'Going to {name}')
    nav.goToPose(make_pose(nav, *STATIONS[name]))
    while not nav.isTaskComplete():
        pass  # isTaskComplete() spins the node briefly each call
    result = nav.getResult()
    if result == TaskResult.SUCCEEDED:
        nav.get_logger().info(f'Reached {name}')
        return True
    nav.get_logger().error(f'Failed to reach {name}: {result}')
    return False


def main():
    rclpy.init()
    nav = BasicNavigator()
    nav.waitUntilNav2Active()

    for station in ('pickup', 'dropoff', 'home'):
        if not go_to(nav, station):
            break
        if station != 'home':
            input(f'At {station}. Press Enter when loading/unloading is done... ')

    nav.lifecycleShutdown() if False else None  # keep Nav2 running
    rclpy.shutdown()


if __name__ == '__main__':
    main()