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

ROI (Region of Interest) cropping:
    Since the camera is fixed and angled at a known mounting position,
    the playing field always projects to roughly the same region of
    each frame. We crop out everything else (ceiling/background above
    the track, the car's own chassis/bumper if visible, and anything
    off to the sides beyond the track boundaries) BEFORE thresholding.
    This reduces false positives from objects outside the field of
    play and speeds up processing (smaller array for cvtColor/inRange/
    contour finding).

    ROI_TOP/ROI_BOTTOM/ROI_LEFT/ROI_RIGHT must be tuned once for your
    specific camera mounting angle/height. Use calibration/roi_tune.py
    (or manually inspect a saved frame with a grid overlay) to find
    values that keep the track floor in-frame while cutting everything
    else out.

Multiple candidates per color:
    Rather than collapsing each color down to a single "biggest blob"
    before the state machine ever sees it, this module reports up to
    MAX_CANDIDATES_PER_COLOR contours per color. This matters when two
    same-color pillars are both in frame at once (e.g. one right in
    front of the robot, another farther down the track) - pixel area
    alone can be fooled by viewing angle or partial cropping at the ROI
    edge, so the state machine should correlate each candidate's
    center_x against the lidar's angular sweep and act on whichever
    candidate has the shortest LIDAR-CONFIRMED distance, not whichever
    has the largest pixel area.

Usage:
    vision = CameraVision()
    vision.start()
    ...
    result = vision.get_detection()
    # result = {
    #     "candidates": [
    #         {"color": "red"/"green", "center_x": int, "area": int},
    #         ...  up to MAX_CANDIDATES_PER_COLOR per color, sorted by
    #              area (largest first) within each color
    #     ]
    # }
    # center_x is reported in FULL-FRAME coordinates (ROI offset already
    # added back in), so it stays consistent with the lidar correlation
    # logic in the state machine.
    #
    # For convenience/back-compat, get_detection() also still exposes
    # "color"/"center_x"/"area" for the single largest candidate overall
    # (across both colors) - but new state-machine code should iterate
    # "candidates" and use lidar distance to choose, not this field.
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

# ROI (Region of Interest) crop bounds, in full-frame pixel coordinates.
# TUNE THESE for your camera's mounting height/angle. Defaults below are
# a starting guess assuming the camera is angled down slightly and the
# track fills the lower-middle portion of the frame.
ROI_TOP = 400       # 30px slice top bound
ROI_BOTTOM = 430    # 30px slice bottom bound
ROI_LEFT = 60       # columns left of this are ignored (outside track boundary)
ROI_RIGHT = 580     # columns right of this are ignored (outside track boundary)

# HSV thresholds - START HERE, then tune with calibration/hsv_tune.py
# Red wraps around the HSV hue circle (0 and 180), so it needs two ranges.
RED_RANGES = [
    ((0, 120, 70), (10, 255, 255)),
    ((170, 120, 70), (180, 255, 255)),
]
GREEN_RANGE = ((40, 70, 70), (85, 255, 255))

MIN_CONTOUR_AREA = 50  # Lowered from 400 since the vertical slice is now only 30px high
MAX_CANDIDATES_PER_COLOR = 3  # cap how many blobs per color we report
FLIP_MODE = -1  # -1 = 180 degree rotation, 0 = vertical flip, 1 = horizontal flip, None = no flip


class CameraVision:
    def __init__(self, frame_w=FRAME_W, frame_h=FRAME_H,
                 roi_top=ROI_TOP, roi_bottom=ROI_BOTTOM,
                 roi_left=ROI_LEFT, roi_right=ROI_RIGHT,
                 flip_mode=FLIP_MODE):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.flip_mode = flip_mode

        # Clamp ROI to valid frame bounds so a bad tune value can't crash cv2.
        self.roi_top = max(0, min(roi_top, frame_h - 1))
        self.roi_bottom = max(self.roi_top + 1, min(roi_bottom, frame_h))
        self.roi_left = max(0, min(roi_left, frame_w - 1))
        self.roi_right = max(self.roi_left + 1, min(roi_right, frame_w))

        self._picam2 = None
        self._thread = None
        self._running = False

        self._lock = threading.Lock()
        self._detection = {"color": None, "center_x": None, "area": 0, "candidates": []}
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
            frame = self._picam2.capture_array()  # RGB888, full frame
            if self.flip_mode is not None:
                frame = cv2.flip(frame, self.flip_mode)

            # Crop to ROI: cheaper processing + ignores anything
            # outside the field of play (background, chassis, off-track).
            roi = frame[self.roi_top:self.roi_bottom, self.roi_left:self.roi_right]

            # NOTE: picamera2's "RGB888" format is actually delivered in
            # BGR byte order in memory (a well-known libcamera/picamera2
            # quirk - the name refers to the format string, not the actual
            # channel order). Using COLOR_RGB2HSV here would swap the red
            # and blue channels before hue conversion, causing red objects
            # to be missed or misclassified (e.g. showing up as green).
            # COLOR_BGR2HSV is the correct conversion for this data.
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            red_mask = self._mask_for_ranges(hsv, RED_RANGES)
            green_mask = self._mask_for_ranges(hsv, [GREEN_RANGE])

            # Get up to MAX_CANDIDATES_PER_COLOR blobs per color instead of
            # collapsing to one - lets the state machine correlate each
            # against the lidar sweep and pick the truly nearest pillar,
            # rather than trusting pixel area (which angle/cropping can fool).
            red_candidates = self._find_candidates(red_mask, "red")
            green_candidates = self._find_candidates(green_mask, "green")
            all_candidates = red_candidates + green_candidates

            with self._lock:
                if not all_candidates:
                    self._detection = {
                        "color": None,
                        "center_x": None,
                        "area": 0,
                        "candidates": [],
                    }
                else:
                    # cx is relative to the ROI crop; add the left offset back
                    # so downstream code (lidar correlation) sees full-frame
                    # coordinates, same as before ROI cropping was added.
                    candidates_full = [
                        {"color": color, "center_x": cx + self.roi_left, "area": area}
                        for (color, cx, area) in all_candidates
                    ]
                    # Back-compat single-best fields = largest blob overall.
                    best = max(candidates_full, key=lambda c: c["area"])
                    self._detection = {
                        "color": best["color"],
                        "center_x": best["center_x"],
                        "area": best["area"],
                        "candidates": candidates_full,
                    }
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
    def _find_candidates(mask, color_label):
        """Return up to MAX_CANDIDATES_PER_COLOR contours for this color,
        as (color_label, center_x, area) tuples, sorted largest-first.
        center_x is relative to the ROI crop; caller adds roi_left back
        to convert to full-frame coordinates.
        """
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        scored = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_CONTOUR_AREA:
                continue
            x, y, w, h = cv2.boundingRect(c)
            center_x = x + w // 2
            scored.append((color_label, center_x, area))

        scored.sort(key=lambda t: t[2], reverse=True)
        return scored[:MAX_CANDIDATES_PER_COLOR]


if __name__ == "__main__":
    # Quick standalone test: print detections at ~5Hz
    vision = CameraVision()
    vision.start()
    try:
        while True:
            time.sleep(0.2)
            d = vision.get_detection()
            print(f"best: color={d['color']} center_x={d['center_x']} area={d['area']} "
                  f"stale={vision.is_stale()} | all candidates: {d['candidates']}")
    except KeyboardInterrupt:
        pass
    finally:
        vision.stop()