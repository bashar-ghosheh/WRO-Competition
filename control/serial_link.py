"""
serial_link.py

Owns the USB-serial connection to the ESP32-S3 (connected via USB-A on
the Pi to USB-C on the ESP32 - the ESP32's native USB-serial bridge).
Takes whatever target_angle / target_speed the state machine last
computed and writes it as a simple ASCII command line, at a fixed rate,
on its own thread.

Protocol (must match the ESP32 sketch exactly - ESP32 side uses the
default `Serial` object since it's USB, not Serial1/GPIO UART):
    "S<angle>,<speed>\n"
    e.g. "S92,180\n"

    angle: servo write value, 0-180 (int)
    speed: motor PWM/speed value, -255..255 (int; sign = direction, if used)

Port note:
    Over USB the ESP32 will show up as /dev/ttyUSB0 or /dev/ttyACM0
    depending on its USB-serial chip - check with:
        dmesg | tail -20
        ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
    after plugging it in. If you also have a USB-serial lidar adapter,
    double check dmesg carefully so you don't mix up which device node
    is which - device assignment order isn't guaranteed across reboots.
    Consider a udev rule to pin a stable name if this bites you.

Reconnect note:
    Unlike a fixed GPIO UART, a USB connection can be unplugged, or the
    ESP32 can reset/re-enumerate (e.g. after a firmware flash), which
    changes or drops the device node. This version retries opening the
    port if it disappears, instead of just dying silently.

Decoupling note:
    This runs its own send-rate loop independent of how fast the state
    machine computes new targets. If the state machine is momentarily
    slow (e.g. a vision frame takes longer), serial_link just re-sends
    the last known target rather than stalling - the ESP32's own
    watchdog handles the case where targets go stale for too long.

Usage:
    link = SerialLink(port="/dev/ttyUSB0", baud=115200, send_hz=30)
    link.start()
    ...
    link.set_target(angle=95, speed=150)   # called by state machine each cycle
    ...
    link.stop()
"""

import glob
import threading
import time

import serial


class SerialLink:
    def __init__(self, port="/dev/ttyAMA4", baud=115200, send_hz=30, log_path=None,
                 auto_detect=True):
        self.port = port
        self.baud = baud
        self.send_interval = 1.0 / send_hz
        self.auto_detect = auto_detect

        self._ser = None
        self._thread = None
        self._running = False
        self._connected = False

        self._lock = threading.Lock()
        self._target_angle = 90   # neutral/straight, matches your servo calibration
        self._target_speed = 0    # stopped by default until state machine says otherwise

        self._log_path = log_path
        self._log_file = None

    def start(self):
        if self._log_path:
            self._log_file = open(self._log_path, "a", buffering=1)

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._ser:
            try:
                self._ser.write(b"S90,0\n")  # final stop command before closing
            except serial.SerialException:
                pass
            self._ser.close()
        if self._log_file:
            self._log_file.close()

    def set_target(self, angle, speed):
        """Called by the state machine every cycle with its latest computed targets."""
        angle = int(max(0, min(180, angle)))     # clamp to valid servo range
        speed = int(max(-255, min(255, speed)))  # clamp to valid motor range
        with self._lock:
            self._target_angle = angle
            self._target_speed = speed

    def emergency_stop(self):
        """Immediately zero speed, keep last steering angle. Call on fault conditions
        (e.g. lidar/camera stale, unexpected exception in the state machine, or
        this link being disconnected)."""
        with self._lock:
            self._target_speed = 0

    def is_connected(self):
        return self._connected

    # -- internals --------------------------------------------------------

    def _find_port(self):
        """Best-effort auto-detect: prefer the configured port if present,
        otherwise scan common USB and GPIO UART device node patterns."""
        candidates = [self.port] + sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyAMA*"))
        for c in candidates:
            if c and glob.glob(c):
                return c
        return None

    def _try_connect(self):
        port = self._find_port() if self.auto_detect else self.port
        if not port:
            return False
        try:
            self._ser = serial.Serial(port, self.baud, timeout=0.1)
            time.sleep(1.5)  # ESP32-S3 USB-CDC typically resets on port open
            self._connected = True
            self.port = port  # remember whichever one actually worked
            return True
        except serial.SerialException:
            self._ser = None
            self._connected = False
            return False

    def _run(self):
        next_send = time.time()
        while self._running:
            if not self._connected:
                if not self._try_connect():
                    time.sleep(0.5)  # USB not present yet / ESP32 not plugged in
                    continue

            now = time.time()
            if now >= next_send:
                with self._lock:
                    angle = self._target_angle
                    speed = self._target_speed

                line = f"S{angle},{speed}\n"
                try:
                    self._ser.write(line.encode("ascii"))
                except serial.SerialException:
                    # cable unplugged or ESP32 re-enumerated (e.g. after reflash)
                    self._connected = False
                    self._ser = None

                if self._log_file:
                    self._log_file.write(f"{now:.3f},{angle},{speed}\n")

                next_send += self.send_interval
                if next_send < now:  # fell behind, resync instead of burst-sending
                    next_send = now + self.send_interval
            else:
                time.sleep(min(0.002, next_send - now))


if __name__ == "__main__":
    # Quick standalone test: sweep the servo target back and forth, speed=0
    link = SerialLink(baud=115200, send_hz=30, auto_detect=True)
    link.start()
    try:
        angle = 90
        direction = 1
        while True:
            angle += direction * 2
            if angle >= 115 or angle <= 50:
                direction *= -1
            link.set_target(angle=angle, speed=0)
            print(f"sent angle={angle} speed=0 connected={link.is_connected()} port={link.port}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        link.stop()