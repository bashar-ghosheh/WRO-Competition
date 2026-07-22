"""
lidar_plot.py

Real-time 2D radar-style plotter for the D500 Lidar.
Draws a visual map of all objects within 3 meters (3000 mm) of the car.
Uses OpenCV for high-speed, zero-dependency rendering on the Pi.

Usage:
    # Ensure virtual environment is active
    python calibration/lidar_plot.py
"""

import math
import time
import cv2
import numpy as np
from lidar.lidar_reader import LidarReader

# Window configuration
WIDTH, HEIGHT = 600, 600
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2

# Range and scaling
MAX_RANGE_MM = 3000.0
SCALE = 280.0 / MAX_RANGE_MM  # Scale 3 meters to fit inside a 280-pixel radius

def main():
    window_name = "WRO 2026 Lidar Map (3 Meters)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Initialize the Lidar Reader (Matches main.py serial port config)
    # Adjust port to /dev/ttyUSB0 or /dev/ttyUSB1 if using a USB adapter
    reader = LidarReader(port="/dev/serial0", baud=230400)
    reader.start()
    
    print("[INFO] Starting Lidar Plotter...")
    time.sleep(1.0) # Settle serial buffer

    try:
        while True:
            # 1. Create a black canvas
            canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

            # 2. Draw grid circles (concentric circles at 1m, 2m, 3m)
            for r_meters in [1.0, 2.0, 3.0]:
                r_pixels = int(r_meters * 1000 * SCALE)
                cv2.circle(canvas, (CENTER_X, CENTER_Y), r_pixels, (50, 50, 50), 1)
                cv2.putText(canvas, f"{int(r_meters)}m", (CENTER_X + r_pixels + 5, CENTER_Y + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)

            # Draw crosshairs
            cv2.line(canvas, (CENTER_X, 0), (CENTER_X, HEIGHT), (40, 40, 40), 1)
            cv2.line(canvas, (0, CENTER_Y), (WIDTH, CENTER_Y), (40, 40, 40), 1)

            # Label center (Robot position)
            cv2.circle(canvas, (CENTER_X, CENTER_Y), 4, (0, 0, 255), -1) # Red center dot
            cv2.putText(canvas, "CAR", (CENTER_X - 12, CENTER_Y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

            # 3. Fetch latest Lidar data snapshot
            distances = reader.get_snapshot()

            # 4. Plot coordinates
            for angle_deg, dist_mm in distances.items():
                if dist_mm == 0 or dist_mm > MAX_RANGE_MM:
                    continue # Ignore out-of-range readings

                # Convert polar coordinates (angle, distance) to Cartesian (x, y)
                # Note: Subtracting 90 degrees aligns 0 degrees to point straight up (forward)
                angle_rad = math.radians(angle_deg - 90)
                
                x = int(CENTER_X + dist_mm * SCALE * math.cos(angle_rad))
                y = int(CENTER_Y + dist_mm * SCALE * math.sin(angle_rad))

                # Draw point (Green circle)
                cv2.circle(canvas, (x, y), 2, (0, 255, 0), -1)

            # 5. Display the canvas
            cv2.imshow(window_name, canvas)

            # Exit on ESC or 'q' key
            key = cv2.waitKey(20) & 0xFF
            if key == 27 or key == ord('q'):
                break

    finally:
        print("[INFO] Stopping Lidar Plotter...")
        reader.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
