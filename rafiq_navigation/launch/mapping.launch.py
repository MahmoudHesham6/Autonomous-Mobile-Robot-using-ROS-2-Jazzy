import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('rafiq_navigation')
    slam_toolbox = get_package_share_directory('slam_toolbox')

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_toolbox, 'launch', 'online_async_launch.py')),
        launch_arguments={
            'slam_params_file': os.path.join(pkg, 'config', 'slam_toolbox.yaml'),
            'use_sim_time': 'true',
        }.items())
    rviz_arg = DeclareLaunchArgument('rviz', default_value='true')
    rviz = Node(
            package='rviz2', executable='rviz2',
            arguments=['-d', os.path.join(pkg, 'rviz', 'mapping.rviz')],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(LaunchConfiguration('rviz')))

    return LaunchDescription([rviz_arg, slam, rviz])