#!/bin/bash
# One-time setup: run with sudo. Makes can0 come up automatically whenever
# the VScom USB-CAN adapter is plugged in, on any USB port.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

install -m 644 "$DIR/99-usb-can.rules" /etc/udev/rules.d/99-usb-can.rules
install -m 644 "$DIR/slcan@.service"   /etc/systemd/system/slcan@.service

# Remove slcand instances started by hand.
pkill -x slcand || true
ip link set can0 down 2>/dev/null || true

systemctl daemon-reload
udevadm control --reload-rules
# Apply to the adapter if it is already plugged in.
udevadm trigger --action=add --subsystem-match=tty

# The service waits 2 s for the adapter before starting slcand.
sleep 4
ip -br link show can0 || echo "can0 not up yet (is the adapter plugged in?)"
