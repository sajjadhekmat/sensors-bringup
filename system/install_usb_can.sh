#!/bin/bash
# One-time setup: run with sudo. Makes can0 come up automatically whenever
# the VScom USB-CAN adapter is plugged in, on any USB port.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

install -m 644 "$DIR/99-usb-can.rules" /etc/udev/rules.d/99-usb-can.rules
install -m 644 "$DIR/slcan@.service"   /etc/systemd/system/slcan@.service
install -m 755 "$DIR/slcan-wait-ready" /usr/local/sbin/slcan-wait-ready

# Remove slcand instances started by hand.
pkill -x slcand || true
ip link set can0 down 2>/dev/null || true

systemctl daemon-reload
udevadm control --reload-rules
# Apply to the adapter if it is already plugged in.
udevadm trigger --action=add --subsystem-match=tty

# The service checks the adapter (up to ~15 s) before starting slcand.
for i in $(seq 30); do [ -e /sys/class/net/can0 ] && break; sleep 0.5; done
ip -br link show can0 || echo "can0 not up yet (is the adapter plugged in?)"
journalctl -u 'slcan@*' -n 10 --no-pager -o cat | grep -E 'Adapter|Trial|No steady' || true
