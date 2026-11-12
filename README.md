# sensors_bringup

ROS 2 bringup package for the **XELA tactile sensors** and the **AIDIN AFT200 force/torque sensor**.
One launch command starts the selected sensors and a status monitor that reports on screen whether each sensor is actually delivering data.

- **ROS 2:** Jazzy (Ubuntu 24.04)
- **Tactile:** XELA sensors over USB-CAN (VScom USB-CAN Plus → SocketCAN `can0`)
- **Force/Torque:** AIDIN AFT200 over UDP Ethernet

---

## Quick start

```bash
source ~/ros_ws/install/setup.bash

ros2 launch sensors_bringup sensors.launch.py                   # both sensors (default)
ros2 launch sensors_bringup sensors.launch.py sensors:=tactile  # tactile only
ros2 launch sensors_bringup sensors.launch.py sensors:=ft       # force/torque only
```

When a sensor is working, the monitor prints:

```
[sensor_status]: XELA: UP (receiving data)
[sensor_status]: AFT200: UP (receiving data)
```

---

## Launch arguments

| Argument          | Default | Description                                                        |
|-------------------|---------|--------------------------------------------------------------------|
| `sensors`         | `both`  | Which sensors to start: `ft`, `tactile`, or `both`                 |
| `startup_timeout` | `10.0`  | Seconds to wait for first data before reporting a sensor as DOWN   |
| `data_timeout`    | `3.0`   | Seconds without new data before reporting a running sensor as lost |

See them anytime with:

```bash
ros2 launch sensors_bringup sensors.launch.py --show-args
```

---

## What gets started

| `sensors:=` | Processes                                                                                   |
|-------------|---------------------------------------------------------------------------------------------|
| `tactile`   | `xela_server`, `xela_service`, `sensor_status`                                              |
| `ft`        | `aft200_node`, `static_transform_publisher` (`fr3_ft_sensor_attachemnt` → `aft200_link`), `sensor_status` |
| `both`      | All of the above                                                                            |

### Topics

| Sensor  | Topic                 | Type                            |
|---------|-----------------------|---------------------------------|
| XELA    | `/xServTopic`         | `xela_server_ros2/SensStream`   |
| AFT200  | `/aidin/wrench_raw`   | `geometry_msgs/WrenchStamped`   |
| AFT200  | `/aidin/wrench`       | `geometry_msgs/WrenchStamped` (bias-compensated) |
| AFT200  | `/aidin/imu`          | `sensor_msgs/Imu`               |
| AFT200  | `/aidin/temperature`  | `sensor_msgs/Temperature`       |

Zero the force/torque sensor (bias) with:

```bash
ros2 service call /aidin/bias std_srvs/srv/Empty
```

### Status monitor

`sensor_status` subscribes to the data topics of the selected sensors and reports:

- **UP** when data starts arriving
- **DOWN** if no data arrives within `startup_timeout`
- **DOWN** if data stops for longer than `data_timeout`

The verbose XELA output is kept in the ROS log (`~/.ros/log/`) instead of the terminal, so the monitor's status lines stay readable.

---

## Installation

### 1. Dependencies

Clone these into the same workspace:

- `xela_server_ros2` — XELA ROS 2 service (provided by XELA Robotics)
- `aft200_ros2` — AIDIN AFT200 driver

Also required:

- XELA server binary at `/home/lasigerobot24/xela_1.8.1/xela_server` with config `/etc/xela/xServ.ini`
  (configured for `bustype = socketcan`, `channel = can0`)
- `can-utils` (provides `slcand`): `sudo apt install can-utils`

### 2. Build

```bash
cd ~/ros_ws/src
git clone git@github.com:sajjadhekmat/sensors-bringup.git sensors_bringup
cd ~/ros_ws
colcon build --packages-select sensors_bringup
source install/setup.bash
```

### 3. One-time USB-CAN setup (tactile sensor)

The XELA sensors need the USB-CAN adapter set up as `can0`. Instead of running `slcand` and `ip link set can0 up` by hand after every replug, install the udev rule and systemd service once:

```bash
sudo ~/ros_ws/src/sensors_bringup/system/install_usb_can.sh
```

After this, `can0` comes up automatically whenever the adapter is plugged in, **on any USB port**, and is shut down cleanly when unplugged.

Check it:

```bash
ip -br link show can0            # should show UP
systemctl status 'slcan@*'       # should show active (running)
```

#### How it works

| File                         | Installed to                            | Purpose                                                                 |
|------------------------------|-----------------------------------------|-------------------------------------------------------------------------|
| `system/99-usb-can.rules`    | `/etc/udev/rules.d/`                    | Identifies the adapter by its USB serial number (not its port) and starts the service on plug-in |
| `system/slcan@.service`      | `/etc/systemd/system/`                  | Runs `slcand -o -s8 -t hw -S 3000000` (1 Mbit/s CAN) to create `can0` and brings it up; stops on unplug |
| `system/install_usb_can.sh`  | —                                       | Copies both files and reloads udev/systemd                              |

> **Using a different adapter?** Edit `ID_SERIAL_SHORT` in `system/99-usb-can.rules`
> (find it with `udevadm info -q property -n /dev/ttyUSB0 | grep ID_SERIAL_SHORT`) and re-run the install script.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `can0 is missing` / `can0 is down` at launch | Plug in the USB-CAN adapter; check `systemctl status 'slcan@*'` |
| `slcand` logs `write: Input/output error` | The adapter is stuck from a previous manual `slcand` run. Unplug and replug it |
| Old failed `slcan@ttyUSBx` entries in `systemctl status` | Harmless leftovers from a previous port; clear with `sudo systemctl reset-failed` |
| `XELA: DOWN` | Check the CAN adapter and sensor power; see the XELA log in `~/.ros/log/` |
| `AFT200: DOWN` | Check the Ethernet connection to the sensor (default `192.168.1.99:8890`) |
| Duplicate nodes / topics | Another launch is still running; stop it with Ctrl+C first |

---

## Package layout

```
sensors_bringup/
├── launch/
│   └── sensors.launch.py        # main launch file (sensors:=ft|tactile|both)
├── sensors_bringup/
│   └── sensor_status.py         # status monitor node
├── system/
│   ├── 99-usb-can.rules         # udev rule for the USB-CAN adapter
│   ├── slcan@.service           # systemd service that creates can0
│   └── install_usb_can.sh       # one-time installer
├── package.xml
└── setup.py
```

## Maintainer

Sajjad Hekmat — shekmat@fc.ul.pt
