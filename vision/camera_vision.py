"""
camera_vision.py

Runs a background thread that grabs frames from the Pi Camera via
picamera2, thresholds for red/green pillars in HSV space, and maintains
a shared, thread-safe "what do I currently see" state for the state
machine to read.

This module answers "what color, and which side is it on" -
NOT "how far away" (that's the lidar's job). Distance/position in the
world comes from correlating the camera's horizontal offset with the
lidar's front-angle cluster in the state machine, not from the camera
alone.

Usage:
    vision = CameraVision()
    vision.start()
    ...
    result = vision.get_detection()
    # result = {"color": "red"/"green"/None, "center_x": int, "area": int}
    ...
    vision.stop()
"""

import threading
import time

import cv2
import numpy as np
from picamera2 import Picamera2

FRAME_W = 640
FRAME_H = 480

# HSV thresholds - START HERE, then tune with calibration/hsv_tune.py
# Red wraps around the HSV hue circle (0 and 180), so it needs two ranges.
RED_RANGES = [
    ((0, 120, 70), (10, 255, 255)),
    ((170, 120, 70), (180, 255, 255)),
]
GREEN_RANGE = ((40, 70, 70), (85, 255, 255))

MIN_CONTOUR_AREA = 400  # pixels; filters out noise/tiny specks


class CameraVision:
    def __init__(self, frame_w=FRAME_W, frame_h=FRAME_H):
        self.frame_w = frame_w
        self.frame_h = frame_h

        self._picam2 = None
        self._thread = None
        self._running = False

        self._lock = threading.Lock()
        self._detection = {"color": None, "center_x": None, "area": 0}
        self._last_update = 0.0

    def start(self):
        self._picam2 = Picamera2()
        config = self._picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (self.frame_w, self.frame_h)}
        )
        self._picam2.configure(config)
        self._picam2.start()
        time.sleep(1.0)  # let auto-exposure/white-balance settle

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._picam2:
            self._picam2.stop()

    def get_detection(self):
        """Return a copy of the latest detection dict."""
        with self._lock:
            return dict(self._detection)

    def is_stale(self, max_age_s=0.3):
        return (time.time() - self._last_update) > max_age_s

    # -- internals --------------------------------------------------------

    def _run(self):
        while self._running:
            frame = self._picam2.capture_array()  # RGB888
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

            red_mask = self._mask_for_ranges(hsv, RED_RANGES)
            green_mask = self._mask_for_ranges(hsv, [GREEN_RANGE])

            red_best = self._largest_contour(red_mask, "red")
            green_best = self._largest_contour(green_mask, "green")

            # Pick whichever color has the larger (closer/more confident) blob
            candidates = [c for c in (red_best, green_best) if c is not None]
            with self._lock:
                if not candidates:
                    self._detection = {"color": None, "center_x": None, "area": 0}
                else:
                    color, cx, area = max(candidates, key=lambda c: c[2])
                    self._detection = {"color": color, "center_x": cx, "area": area}
                self._last_update = time.time()

    @staticmethod
    def _mask_for_ranges(hsv, ranges):
        mask = None
        for lo, hi in ranges:
            m = cv2.inRange(hsv, np.array(lo), np.array(hi))
            mask = m if mask is None else cv2.bitwise_or(mask, m)
        # clean up small noise
        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)
        return mask

    @staticmethod
    def _largest_contour(mask, color_label):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < MIN_CONTOUR_AREA:
            return None
        x, y, w, h = cv2.boundingRect(largest)
        center_x = x + w // 2
        return (color_label, center_x, area)


if __name__ == "__main__":
    # Quick standalone test: print detections at ~5Hz
    vision = CameraVision()
    vision.start()
    try:
        while True:
            time.sleep(0.2)
            d = vision.get_detection()
            print(f"color={d['color']} center_x={d['center_x']} area={d['area']} stale={vision.is_stale()}")
    except KeyboardInterrupt:
        pass
    finally:
        vision.stop()