import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory('rafiq_navigation')
    nav2_bringup = get_package_share_directory('nav2_bringup')

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup, 'launch', 'navigation_launch.py')),
        launch_arguments={
            'params_file': os.path.join(pkg, 'config', 'nav2_params.yaml'),
            'use_sim_time': 'true',
            'use_composition': 'False',
        }.items())

    # Nav2 publishes Twist; the diff drive controller wants TwistStamped
    stamper = Node(
        package='twist_stamper', executable='twist_stamper',
        parameters=[{'use_sim_time': True}],
        remappings=[('cmd_vel_in', 'cmd_vel'),
                    ('cmd_vel_out', '/diff_drive_controller/cmd_vel')])

    rviz_arg = DeclareLaunchArgument('rviz', default_value='true')
    rviz = Node(
        package='rviz2', executable='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'navigation.rviz')],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')))
    return LaunchDescription([rviz_arg, navigation, stamper, rviz])