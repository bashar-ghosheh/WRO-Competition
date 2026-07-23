"""
state_machine.py

The central control logic for the autonomous car. 
Reads states from CameraVision and LidarReader, processes the navigation rules,
and sends steering and speed targets to SerialLink.

WRO Future Engineers Rule Reference:
- Red pillars must be kept on the right (pass on the left side / steer left).
- Green pillars must be kept on the left (pass on the right side / steer right).
- Navigating the track for 3 full laps.
"""

import time
import logging

class StateMachine:
    # Steering constants (calibrated to the physical servo mapping)
    STEER_CENTER = 90
    STEER_MAX_LEFT = 60
    STEER_MAX_RIGHT = 120

    # Driving speed targets
    SPEED_NORMAL = 100
    SPEED_SLOW = 70
    SPEED_STOP = 0

    def __init__(self, vision, lidar, serial_link, loop_hz=20):
        self.vision = vision
        self.lidar = lidar
        self.serial_link = serial_link
        self.loop_interval = 1.0 / loop_hz
        
        self.running = False
        self.state = "STARTING"
        self.laps_completed = 0
        
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        self.logger = logging.getLogger("StateMachine")

    def start(self):
        self.running = True
        self.logger.info("State Machine started.")
        self._run()

    def stop(self):
        self.running = False
        self.serial_link.emergency_stop()
        self.logger.info("State Machine stopped. Emergency stop sent.")

    def _run(self):
        while self.running:
            start_time = time.time()
            
            # 1. Safety Check: If serial, lidar, or camera are disconnected/stale, stop!
            if not self.serial_link.is_connected():
                self.logger.warning("Serial link disconnected! Emergency stopping.")
                self.serial_link.emergency_stop()
                time.sleep(0.1)
                continue

            if self.lidar.is_stale(max_age_s=0.5) or self.vision.is_stale(max_age_s=0.5):
                self.logger.warning("Sensors are stale! Lidar stale: %s, Vision stale: %s", 
                                    self.lidar.is_stale(), self.vision.is_stale())
                self.serial_link.emergency_stop()
                time.sleep(0.1)
                continue

            # 2. Get latest sensor snapshots
            detection = self.vision.get_detection()
            lidar_snapshot = self.lidar.get_snapshot()

            # 3. Process states
            target_steer = self.STEER_CENTER
            target_speed = self.SPEED_NORMAL

            if self.state == "STARTING":
                self.state = "WALL_FOLLOWING"
                self.logger.info("Transition to WALL_FOLLOWING")

            elif self.state == "WALL_FOLLOWING":
                target_steer = self._handle_wall_following(lidar_snapshot)
                
                # Check for camera obstacles
                if detection["color"] is not None and detection["area"] > 800:
                    self.state = "AVOIDING_OBSTACLE"
                    self.logger.info("Transition to AVOIDING_OBSTACLE. Saw color: %s", detection["color"])

            elif self.state == "AVOIDING_OBSTACLE":
                if detection["color"] is None or detection["area"] < 500:
                    self.state = "WALL_FOLLOWING"
                    self.logger.info("Transition back to WALL_FOLLOWING. Obstacle cleared.")
                else:
                    target_steer, target_speed = self._handle_obstacle_avoidance(detection, lidar_snapshot)

            # 4. Command the actuators
            self.serial_link.set_target(angle=target_steer, speed=target_speed)

            # Control frequency
            elapsed = time.time() - start_time
            sleep_time = self.loop_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _get_sector_min(self, distances, start_angle, end_angle):
        """
        Finds the minimum distance within an angular sector arc.
        By geometric projection, the minimum distance to a straight wall across a sector
        is ALWAYS the true perpendicular distance, making wall-following completely
        immune to car tilt or vehicle yaw rotation!
        Filters out self-reflections (<100mm) and out-of-range readings.
        """
        valid_pts = [
            distances[a] for a in range(start_angle, end_angle + 1)
            if a in distances and 100 <= distances[a] <= 4000
        ]
        return min(valid_pts) if valid_pts else None

    def _handle_wall_following(self, distances):
        """
        Uses Sector Minimum Projection to follow walls smoothly.
        Compares true perpendicular left (60°-120° arc) and right (240°-300° arc) wall distances.
        """
        # Search a 60-degree sector arc around left (60°-120°) and right (240°-300°)
        left_dist = self._get_sector_min(distances, 60, 120)
        right_dist = self._get_sector_min(distances, 240, 300)

        if left_dist is None or right_dist is None:
            # Missing side readings, maintain center
            return self.STEER_CENTER

        # Calculate error: positive means too close to left wall, steer right
        error = left_dist - right_dist
        
        # P control gain (tuned to map millimeter differences to servo degrees)
        kp = 0.05 
        steer_offset = int(error * kp)
        
        target_steer = self.STEER_CENTER + steer_offset
        return max(self.STEER_MAX_LEFT, min(self.STEER_MAX_RIGHT, target_steer))

    def _handle_obstacle_avoidance(self, detection, distances):
        """
        Steers around detected red or green pillars.
        - Red pillar: Must be passed on the LEFT (steer left to keep it on the right)
        - Green pillar: Must be passed on the RIGHT (steer right to keep it on the left)
        """
        color = detection["color"]
        center_x = detection["center_x"]
        
        target_speed = self.SPEED_SLOW
        
        if color == "red":
            # Steer Left
            target_steer = self.STEER_CENTER - 25  # Apply hard left offset
            self.logger.info("Avoiding RED: steering left")
        elif color == "green":
            # Steer Right
            target_steer = self.STEER_CENTER + 25  # Apply hard right offset
            self.logger.info("Avoiding GREEN: steering right")
        else:
            target_steer = self.STEER_CENTER

        target_steer = max(self.STEER_MAX_LEFT, min(self.STEER_MAX_RIGHT, target_steer))
        return target_steer, target_speed
