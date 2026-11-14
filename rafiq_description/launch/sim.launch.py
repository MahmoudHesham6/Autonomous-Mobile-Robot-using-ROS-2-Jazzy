import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg = get_package_share_directory('rafiq_description')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    xacro_file = os.path.join(pkg, 'urdf', 'rafiq.urdf.xacro')
    world = os.path.join(pkg, 'worlds', 'room.sdf')
    bridge_cfg = os.path.join(pkg, 'config', 'bridge.yaml')
    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': f'-r {world}'}.items())

    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               parameters=[{'robot_description': robot_description,
                            'use_sim_time': True}])

    spawn = Node(package='ros_gz_sim', executable='create',
                 arguments=['-name', 'rafiq', '-topic', 'robot_description', '-z', '0.1'])

    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge',
                  parameters=[{'config_file': bridge_cfg, 'use_sim_time': True}])

    jsb = Node(package='controller_manager', executable='spawner',
               arguments=['joint_state_broadcaster',
                          '--controller-manager-timeout', '60',
                          '--switch-timeout', '30'])
    ddc = Node(package='controller_manager', executable='spawner',
               arguments=['diff_drive_controller',
                          '--controller-manager-timeout', '60',
                          '--switch-timeout', '30'])
    ekf = Node(package='robot_localization', executable='ekf_node',
           name='ekf_filter_node', output='screen',
           parameters=[os.path.join(pkg, 'config', 'ekf.yaml')])
    # Controllers can only start once the robot (and its controller manager) exists
    after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn, on_exit=[jsb]))
    after_jsb = RegisterEventHandler(
        OnProcessExit(target_action=jsb, on_exit=[ddc]))

    rviz_arg = DeclareLaunchArgument(
    'rviz', default_value='false', description='Open RViz')

    rviz = Node(
    package='rviz2', executable='rviz2',
    arguments=['-d', os.path.join(pkg, 'rviz', 'sim.rviz')],
    parameters=[{'use_sim_time': True}],
    condition=IfCondition(LaunchConfiguration('rviz')))

    return LaunchDescription([rviz_arg, gz, rsp, spawn, bridge, ekf, rviz, after_spawn, after_jsb])