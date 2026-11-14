import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    description = get_package_share_directory('rafiq_description')
    navigation = get_package_share_directory('rafiq_navigation')

    def include(pkg_dir, name, args=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg_dir, 'launch', name)),
            launch_arguments=(args or {}).items())

    rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true',
                                     description='Open the navigation RViz view')

    sim = include(description, 'sim.launch.py', {'rviz': 'false'})

    localization = TimerAction(
        period=10.0, actions=[include(navigation, 'localization.launch.py')])

    nav = TimerAction(
        period=15.0,
        actions=[include(navigation, 'navigation.launch.py', {'rviz': 'false'})])

    rviz = TimerAction(
        period=15.0,
        actions=[Node(
            package='rviz2', executable='rviz2', output='screen',
            arguments=['-d', os.path.join(navigation, 'rviz', 'navigation.rviz')],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(LaunchConfiguration('use_rviz')))])

    mission = TimerAction(
        period=18.0,
        actions=[Node(package='rafiq_mission', executable='mission_server',
                      output='screen',
                      arguments=['--ros-args', '-p', 'use_sim_time:=true'])])

    return LaunchDescription([rviz_arg, sim, localization, nav, rviz, mission])
