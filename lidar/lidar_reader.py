"""
lidar_reader.py

Reads the D500 (LDROBOT LD19 / STL-19P core) lidar over UART and maintains
a shared, thread-safe angle -> distance(mm) map that other threads
(vision, state machine) can read at any time. Handles optional PWM motor pin (GPIO 12).

Packet format (LD19 standard, 47 bytes per packet):
  byte 0      : header, always 0x54
  byte 1      : ver_len  (bits 0-4 = number of points in this packet, usually 12)
  bytes 2-3   : radar speed, uint16 LE, deg/s
  bytes 4-5   : start_angle, uint16 LE, units of 0.01 degree
  bytes 6..41 : 12 points x 3 bytes each = 36 bytes
                  each point: distance uint16 LE (mm), intensity uint8
  bytes 42-43 : end_angle, uint16 LE, units of 0.01 degree
  bytes 44-45 : timestamp, uint16 LE, ms
  byte 46     : crc8 checksum over bytes 0-45
"""

import threading
import serial
import time

POINTS_PER_PACKET = 12
PACKET_LEN = 47
HEADER = 0x54

# Standard LD19/STL-19P CRC8 lookup table (polynomial used by LDROBOT SDK)
CRC_TABLE = [
    0x00, 0x4d, 0x9a, 0xd7, 0x79, 0x34, 0xe3, 0xae, 0xf2, 0xbf, 0x68, 0x25,
    0x8b, 0xc6, 0x11, 0x5c, 0xa9, 0xe4, 0x33, 0x7e, 0xd0, 0x9d, 0x4a, 0x07,
    0x5b, 0x16, 0xc1, 0x8c, 0x22, 0x6f, 0xb8, 0xf5, 0x1f, 0x52, 0x85, 0xc8,
    0x66, 0x2b, 0xfc, 0xb1, 0xed, 0xa0, 0x77, 0x3a, 0x94, 0xd9, 0x0e, 0x43,
    0xb6, 0xfb, 0x2c, 0x61, 0xcf, 0x82, 0x55, 0x18, 0x44, 0x09, 0xde, 0x93,
    0x3d, 0x70, 0xa7, 0xea, 0x3e, 0x73, 0xa4, 0xe9, 0x47, 0x0a, 0xdd, 0x90,
    0xcc, 0x81, 0x56, 0x1b, 0xb5, 0xf8, 0x2f, 0x62, 0x97, 0xda, 0x0d, 0x40,
    0xee, 0xa3, 0x74, 0x39, 0x65, 0x28, 0xff, 0xb2, 0x1c, 0x51, 0x86, 0xcb,
    0x21, 0x6c, 0xbb, 0xf6, 0x58, 0x15, 0xc2, 0x8f, 0xd3, 0x9e, 0x49, 0x04,
    0xaa, 0xe7, 0x30, 0x7d, 0x88, 0xc5, 0x12, 0x5f, 0xf1, 0xbc, 0x6b, 0x26,
    0x7a, 0x37, 0xe0, 0xad, 0x03, 0x4e, 0x99, 0xd4, 0x7c, 0x31, 0xe6, 0xab,
    0x05, 0x48, 0x9f, 0xd2, 0x8e, 0xc3, 0x14, 0x59, 0xf7, 0xba, 0x6d, 0x20,
    0xd5, 0x98, 0x4f, 0x02, 0xac, 0xe1, 0x36, 0x7b, 0x27, 0x6a, 0xbd, 0xf0,
    0x5e, 0x13, 0xc4, 0x89, 0x63, 0x2e, 0xf9, 0xb4, 0x1a, 0x57, 0x80, 0xcd,
    0x91, 0xdc, 0x0b, 0x46, 0xe8, 0xa5, 0x72, 0x3f, 0xca, 0x87, 0x50, 0x1d,
    0xb3, 0xfe, 0x29, 0x64, 0x38, 0x75, 0xa2, 0xef, 0x41, 0x0c, 0xdb, 0x96,
    0x42, 0x0f, 0xd8, 0x95, 0x3b, 0x76, 0xa1, 0xec, 0xb0, 0xfd, 0x2a, 0x67,
    0xc9, 0x84, 0x53, 0x1e, 0xeb, 0xa6, 0x71, 0x3c, 0x92, 0xdf, 0x08, 0x45,
    0x19, 0x54, 0x83, 0xce, 0x60, 0x2d, 0xfa, 0xb7, 0x5d, 0x10, 0xc7, 0x8a,
    0x24, 0x69, 0xbe, 0xf3, 0xaf, 0xe2, 0x35, 0x78, 0xd6, 0x9b, 0x4c, 0x01,
    0xf4, 0xb9, 0x6e, 0x23, 0x8d, 0xc0, 0x17, 0x5a, 0x06, 0x4b, 0x9c, 0xd1,
    0x7f, 0x32, 0xe5, 0xa8,
]


def crc8(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = CRC_TABLE[(crc ^ b) & 0xFF]
    return crc


class LidarReader:
    def __init__(self, port="/dev/serial0", baud=230400, max_range_mm=8000, pwm_pin=12):
        self.port = port
        self.baud = baud
        self.max_range_mm = max_range_mm
        self.pwm_pin = pwm_pin
        self._pwm_obj = None

        self._ser = None
        self._thread = None
        self._running = False

        self._lock = threading.Lock()
        self._distances = {}
        self._last_update = 0.0

    def start(self):
        # 1. Initialize PWM pin for Lidar motor spinning if specified
        if self.pwm_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pwm_pin, GPIO.OUT)
                self._pwm_obj = GPIO.PWM(self.pwm_pin, 1000)  # 1kHz PWM frequency
                self._pwm_obj.start(100)                      # 100% duty cycle full speed
            except Exception as e:
                print(f"[WARN] Lidar PWM pin setup skipped: {e}")

        # 2. Open Serial connection
        self._ser = serial.Serial(self.port, self.baud, timeout=0.1)
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._ser:
            self._ser.close()
        if self._pwm_obj:
            try:
                self._pwm_obj.stop()
                import RPi.GPIO as GPIO
                GPIO.cleanup(self.pwm_pin)
            except Exception:
                pass

    def get_distance(self, angle_deg):
        """Return distance in mm at the given integer angle (0-359), or None if no data yet."""
        angle_deg = int(angle_deg) % 360
        with self._lock:
            return self._distances.get(angle_deg)

    def get_snapshot(self):
        """Return a copy of the full angle->distance map."""
        with self._lock:
            return dict(self._distances)

    def is_stale(self, max_age_s=0.5):
        return (time.time() - self._last_update) > max_age_s

    # -- internals --------------------------------------------------------

    def _run(self):
        buf = bytearray()
        while self._running:
            chunk = self._ser.read(256)
            if not chunk:
                continue
            buf.extend(chunk)

            while True:
                idx = buf.find(HEADER)
                if idx == -1:
                    buf.clear()
                    break
                if idx > 0:
                    del buf[:idx]
                if len(buf) < PACKET_LEN:
                    break

                packet = bytes(buf[:PACKET_LEN])
                if crc8(packet[:-1]) == packet[-1]:
                    self._parse_packet(packet)
                    del buf[:PACKET_LEN]
                else:
                    del buf[:1]

    def _parse_packet(self, packet: bytes):
        start_angle = int.from_bytes(packet[4:6], "little") / 100.0
        end_angle = int.from_bytes(packet[42:44], "little") / 100.0

        angle_span = end_angle - start_angle
        if angle_span < 0:
            angle_span += 360.0

        step = angle_span / max(POINTS_PER_PACKET - 1, 1)

        with self._lock:
            for i in range(POINTS_PER_PACKET):
                offset = 6 + i * 3
                dist_mm = int.from_bytes(packet[offset:offset + 2], "little")

                if dist_mm == 0 or dist_mm > self.max_range_mm:
                    continue

                angle = (start_angle + step * i) % 360.0
                self._distances[int(angle)] = dist_mm

            self._last_update = time.time()


if __name__ == "__main__":
    reader = LidarReader("/dev/serial0", 230400, pwm_pin=12)
    reader.start()
    try:
        while True:
            time.sleep(0.2)
            front = reader.get_distance(0)
            left = reader.get_distance(90)
            right = reader.get_distance(270)
            print(f"front={front} left={left} right={right} stale={reader.is_stale()}")
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()