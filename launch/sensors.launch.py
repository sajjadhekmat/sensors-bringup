import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.logging import get_logger
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

SENSOR_CHOICES = ('ft', 'tactile', 'both')


def _report_exit(name, action):
    def report_nonzero_exit(event, _context):
        if event.returncode != 0:
            get_logger('launch').error(
                f'{name} stopped with exit code {event.returncode}.'
            )

    return RegisterEventHandler(
        OnProcessExit(
            target_action=action,
            on_exit=report_nonzero_exit,
        )
    )


def _check_can0():
    # The XELA tactile sensor uses can0, which is brought up by
    # udev + slcan@.service (see system/).
    try:
        with open('/sys/class/net/can0/operstate') as f:
            state = f.read().strip()
    except OSError:
        state = 'missing'
    if state not in ('up', 'unknown'):
        get_logger('launch').error(
            f'can0 is {state}. Is the USB-CAN adapter plugged in? '
            'Check: systemctl status "slcan@*"'
        )


def _tactile_actions():
    _check_can0()

    xela_launch_dir = os.path.dirname(
        os.path.join(
            get_package_share_directory('xela_server_ros2'),
            'launch',
            'service.launch',
        )
    )

    # XELA writes large amounts of unstructured INFO output. Keep it in the
    # ROS log; sensor_status reports actual readiness on screen.
    xela_server = ExecuteProcess(
        cmd=[
            '/home/lasigerobot24/xela_1.8.1/xela_server',
            '-f',
            '/etc/xela/xServ.ini',
        ],
        output='log',
        cwd=xela_launch_dir,
    )

    xela_service = Node(
        package='xela_server_ros2',
        executable='xela_service',
        name='xela_service',
        output='log',
        parameters=[{'port': 5000, 'ip': '127.0.0.1', 'd': 0}],
    )

    return [
        xela_server,
        xela_service,
        _report_exit('XELA server', xela_server),
        _report_exit('XELA ROS service', xela_service),
    ]


def _ft_actions():
    aft200 = Node(
        package='aft200_ros2',
        executable='aft200_node',
        name='aft200_node',
        output='screen',
        parameters=[{'frame_id': 'fr3_ft_sensor_attachemnt'}],
        arguments=['--ros-args', '--log-level', 'warn'],
    )

    aft200_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='aft200_static_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'fr3_ft_sensor_attachemnt',
            '--child-frame-id', 'aft200_link',
        ],
    )

    return [
        aft200,
        aft200_static_tf,
        _report_exit('AFT200 driver', aft200),
    ]


def _launch_setup(context):
    sensors = LaunchConfiguration('sensors').perform(context).strip().lower()
    if sensors not in SENSOR_CHOICES:
        raise RuntimeError(
            f"Invalid sensors:='{sensors}'. "
            f"Choose one of: {', '.join(SENSOR_CHOICES)}."
        )

    use_tactile = sensors in ('tactile', 'both')
    use_ft = sensors in ('ft', 'both')

    monitored = []
    actions = []
    if use_tactile:
        actions += _tactile_actions()
        monitored.append('XELA')
    if use_ft:
        actions += _ft_actions()
        monitored.append('AFT200')

    get_logger('launch').info(f'Starting sensors: {", ".join(monitored)}')

    sensor_status = Node(
        package='sensors_bringup',
        executable='sensor_status',
        name='sensor_status',
        output='screen',
        parameters=[{
            'sensors': monitored,
            'startup_timeout': LaunchConfiguration('startup_timeout'),
            'data_timeout': LaunchConfiguration('data_timeout'),
        }],
    )

    return actions + [
        sensor_status,
        _report_exit('Sensor status monitor', sensor_status),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'sensors',
            default_value='both',
            choices=list(SENSOR_CHOICES),
            description='Which sensors to start: ft (force/torque), '
                        'tactile (XELA), or both.',
        ),
        DeclareLaunchArgument(
            'startup_timeout',
            default_value='10.0',
            description='Seconds to wait before reporting a sensor as down.',
        ),
        DeclareLaunchArgument(
            'data_timeout',
            default_value='3.0',
            description='Seconds without data before reporting a sensor lost.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
