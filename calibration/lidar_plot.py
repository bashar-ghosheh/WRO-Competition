"""
lidar_plot.py

A headless 2D radar-style plotter web server for the D500 Lidar.
Draws a visual map of all objects within 3 meters and streams it over HTTP.
This avoids OpenCV GUI window crashes (xcb/display errors) on headless Raspberry Pi setups.

How to view:
    Open your browser (on PC or phone on the same Wi-Fi) and go to:
    http://<your_pi_ip_address>:8001
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import cv2
import numpy as np
from lidar.lidar_reader import LidarReader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Window configuration
WIDTH, HEIGHT = 600, 600
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2

# Range and scaling
MAX_RANGE_MM = 1000.0
SCALE = 280.0 / MAX_RANGE_MM  # Scale 1 meter to fit inside a 280-pixel radius

class LidarStreamer:
    def __init__(self):
        self.reader = LidarReader(port="/dev/serial0", baud=230400)
        self.reader.start()
        time.sleep(1.0) # Settle serial buffer
        logging.info("Lidar Streamer initialized.")

    def get_jpeg_frame(self):
        # 1. Create a black canvas
        canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        # 2. Draw grid circles (concentric circles at 0.25m, 0.5m, 0.75m, 1m)
        for r_meters in [0.25, 0.5, 0.75, 1.0]:
            r_pixels = int(r_meters * 1000 * SCALE)
            cv2.circle(canvas, (CENTER_X, CENTER_Y), r_pixels, (50, 50, 50), 1)
            cv2.putText(canvas, f"{r_meters}m", (CENTER_X + r_pixels + 5, CENTER_Y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)

        # Draw crosshairs
        cv2.line(canvas, (CENTER_X, 0), (CENTER_X, HEIGHT), (40, 40, 40), 1)
        cv2.line(canvas, (0, CENTER_Y), (WIDTH, CENTER_Y), (40, 40, 40), 1)

        # Label center (Robot position)
        cv2.circle(canvas, (CENTER_X, CENTER_Y), 4, (0, 0, 255), -1) # Red center dot
        cv2.putText(canvas, "CAR", (CENTER_X - 12, CENTER_Y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # 3. Fetch latest Lidar data snapshot
        distances = self.reader.get_snapshot()

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

        # Encode frame to JPEG
        _, jpeg = cv2.imencode('.jpg', canvas)
        return jpeg.tobytes()

    def close(self):
        self.reader.stop()


# MJPEG Server Handler
class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Main landing webpage
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <html>
            <head>
                <title>WRO 2026 Lidar Radar Map</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background: #121212;
                        color: #ffffff;
                        text-align: center;
                        margin: 0;
                        padding: 20px;
                    }
                    h1 { color: #00ff66; }
                    .container { margin-top: 20px; }
                    img {
                        border: 4px solid #333;
                        border-radius: 50%; /* Circle look for radar */
                        max-width: 100%;
                    }
                    .info {
                        margin-top: 15px;
                        color: #888;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <h1>WRO 2026 Lidar Map (3 Meters)</h1>
                <p>Live 2D point cloud visualization.</p>
                <div class="container">
                    <img src="/stream.mjpg" />
                </div>
                <div class="info">
                    Range: 3.0 Meters | Scale: auto
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path == '/stream.mjpg':
            # Stream the MJPEG video feed
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    frame_bytes = streamer.get_jpeg_frame()
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame_bytes))
                    self.end_headers()
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b'\r\n')
                    time.sleep(0.1) # ~10 FPS limit to save CPU/bandwidth
            except Exception as e:
                logging.info(f"Client disconnected: {e}")

        else:
            self.send_error(404)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    # Initialize the lidar streamer globally
    streamer = LidarStreamer()
    # Running on Port 8001 to prevent conflicts with web_tuner.py on Port 8000
    server_address = ('', 8001)
    
    try:
        server = ThreadedHTTPServer(server_address, StreamingHandler)
        logging.info("=========================================")
        logging.info(" Lidar Web Server running on port 8001")
        logging.info(" Open: http://<your_pi_ip_address>:8001")
        logging.info(" Press Ctrl+C to stop.")
        logging.info("=========================================")
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stopping web server...")
    finally:
        streamer.close()
