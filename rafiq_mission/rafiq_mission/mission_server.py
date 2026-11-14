import math
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rafiq_interfaces.action import Deliver
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rafiq_interfaces.msg import RobotStatus
import os
import yaml
from ament_index_python.packages import get_package_share_directory
def load_stations(path):
    with open(path) as f:
        data = yaml.safe_load(f)['stations']
    return {name: (s['x'], s['y'], s['yaw']) for name, s in data.items()}
LOAD_WAIT_SEC = 5.0   # stand-in for a real loading confirmation


def make_pose(nav, x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = nav.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


class MissionServer(Node):
    def __init__(self):
        super().__init__('mission_server')
        self.nav = BasicNavigator()
        self.nav.waitUntilNav2Active()
        self.busy = False
        self.declare_parameter('robot_name', 'rafiq')
        self.state = 'idle'
        self.station = ''
        self.status_pub = self.create_publisher(RobotStatus, 'status', 10)
        self.create_timer(1.0, self.publish_status)
        default = os.path.join(
            get_package_share_directory('rafiq_mission'), 'config', 'stations.yaml')
        self.declare_parameter('stations_file', default)
        self.stations = load_stations(self.get_parameter('stations_file').value)
        if 'home' not in self.stations:
            raise RuntimeError('stations.yaml must define a "home" station')
        self._server = ActionServer(
            self, Deliver, 'deliver',
            execute_callback=self.execute,
            goal_callback=self.on_goal,
            cancel_callback=self.on_cancel,
            callback_group=ReentrantCallbackGroup())
        self.get_logger().info('Mission server ready: action /deliver')

    def publish_status(self):
        msg = RobotStatus()
        msg.robot_name = self.get_parameter('robot_name').value
        msg.state = self.state
        msg.current_station = self.station
        msg.battery = 100.0   # placeholder until there is a real battery source
        msg.busy = self.busy
        self.status_pub.publish(msg)
    def on_goal(self, request):
        if self.busy:
            self.get_logger().warn('Rejected: already on a mission')
            return GoalResponse.REJECT
        for name in (request.pickup, request.dropoff):
            if name not in self.stations:
                self.get_logger().warn(f'Rejected: unknown station "{name}"')
                return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def on_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    def drive(self, goal_handle, station, state):
        self.state, self.station = state, station
        feedback = Deliver.Feedback(state=state, current_station=station)
        goal_handle.publish_feedback(feedback)
        self.nav.goToPose(make_pose(self.nav, *self.stations[station]))
        while not self.nav.isTaskComplete():
            if goal_handle.is_cancel_requested:
                self.nav.cancelTask()
                return 'canceled'
        return 'ok' if self.nav.getResult() == TaskResult.SUCCEEDED else 'failed'

    def wait_for_load(self, goal_handle, station):
        self.state, self.station = 'waiting_for_load', station
        goal_handle.publish_feedback(
            Deliver.Feedback(state='waiting_for_load', current_station=station))
        end = time.time() + LOAD_WAIT_SEC
        while time.time() < end:
            if goal_handle.is_cancel_requested:
                return 'canceled'
            time.sleep(0.2)
        return 'ok'

    def execute(self, goal_handle):
        self.busy = True
        req = goal_handle.request
        result = Deliver.Result()
        steps = [
            ('drive', req.pickup, 'going_to_pickup'),
            ('wait', req.pickup, 'waiting_for_load'),
            ('drive', req.dropoff, 'going_to_dropoff'),
            ('wait', req.dropoff, 'waiting_for_unload'),
            ('drive', 'home', 'returning_home'),
        ]
        outcome, where = 'ok', ''
        try:
            for kind, station, state in steps:
                outcome = (self.drive(goal_handle, station, state) if kind == 'drive'
                           else self.wait_for_load(goal_handle, station))
                if outcome != 'ok':
                    where = station
                    break
        finally:
            self.busy = False
            self.state, self.station = 'idle', ''

        if outcome == 'ok':
            result.success, result.message = True, 'Delivery complete'
            goal_handle.succeed()
        elif outcome == 'canceled':
            result.success, result.message = False, f'Canceled at {where}'
            goal_handle.canceled()
        else:
            result.success, result.message = False, f'Failed on the way to {where}'
            goal_handle.abort()
        return result


def main():
    rclpy.init()
    server = MissionServer()
    executor = MultiThreadedExecutor()
    executor.add_node(server)
    try:
        executor.spin()
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()