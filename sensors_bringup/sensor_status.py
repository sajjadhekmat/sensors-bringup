import time

from geometry_msgs.msg import WrenchStamped
import rclpy
from rclpy.node import Node
from xela_server_ros2.msg import SensStream


class SensorStatus(Node):
    """Print sensor readiness and changes in readiness."""

    def __init__(self):
        super().__init__('sensor_status')
        self.declare_parameter('sensors', ['XELA', 'AFT200'])
        self.declare_parameter('startup_timeout', 10.0)
        self.declare_parameter('data_timeout', 3.0)

        sensors = list(self.get_parameter('sensors').value)

        self.startup_timeout = float(
            self.get_parameter('startup_timeout').value
        )
        self.data_timeout = float(self.get_parameter('data_timeout').value)
        self.started_at = time.monotonic()
        self.last_data = {sensor: None for sensor in sensors}
        self.state = {sensor: 'starting' for sensor in sensors}

        if 'XELA' in sensors:
            self.create_subscription(
                SensStream, '/xServTopic', self._on_xela_data, 10
            )
        if 'AFT200' in sensors:
            self.create_subscription(
                WrenchStamped, '/aidin/wrench_raw', self._on_aft200_data, 10
            )
        self.create_timer(0.5, self._check_status)

    def _on_xela_data(self, message):
        if any(sensor.model != 'not_available' for sensor in message.sensors):
            self._mark_up('XELA')

    def _on_aft200_data(self, _message):
        self._mark_up('AFT200')

    def _mark_up(self, sensor):
        self.last_data[sensor] = time.monotonic()
        if self.state[sensor] != 'up':
            self.state[sensor] = 'up'
            self.get_logger().info(f'{sensor}: UP (receiving data)')

    def _check_status(self):
        now = time.monotonic()
        for sensor in self.state:
            last_data = self.last_data[sensor]
            if last_data is None:
                if (
                    self.state[sensor] == 'starting'
                    and now - self.started_at >= self.startup_timeout
                ):
                    self.state[sensor] = 'down'
                    self.get_logger().warning(
                        f'{sensor}: DOWN (no data received within '
                        f'{self.startup_timeout:.1f} seconds)'
                    )
            elif (
                self.state[sensor] == 'up'
                and now - last_data >= self.data_timeout
            ):
                self.state[sensor] = 'down'
                self.get_logger().warning(
                    f'{sensor}: DOWN (data stopped for '
                    f'{self.data_timeout:.1f} seconds)'
                )


def main(args=None):
    rclpy.init(args=args)
    node = SensorStatus()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
