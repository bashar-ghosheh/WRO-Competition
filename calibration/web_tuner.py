"""
web_tuner.py

A zero-dependency, pure Python web server that streams live video from the Pi Camera.
Draws a green bounding box to show exactly where the camera is being cropped (ROI),
and displays both the full camera view and the cropped region side-by-side.

No libraries needed besides OpenCV and Picamera2.

How to view:
    Open your browser (on PC or phone on the same Wi-Fi) and go to:
    http://<your_pi_ip_address>:8000
"""

import io
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import cv2
import numpy as np
from picamera2 import Picamera2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# --- CONFIGURATION (Must match camera_vision.py) ---
FRAME_W = 640
FRAME_H = 480

ROI_TOP = 400
ROI_BOTTOM = 430
ROI_LEFT = 60
ROI_RIGHT = 580

FLIP_MODE = -1  # -1 = 180 degree rotation, 0 = vertical flip, 1 = horizontal flip, None = no flip

# Class to capture frames from Picamera2 in a background thread
class CameraStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (FRAME_W, FRAME_H)}
        )
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(1.0) # Settle camera exposure
        logging.info("Camera Streamer initialized.")

    def get_jpeg_frame(self):
        # Capture raw frame (in BGR memory layout)
        frame = self.picam2.capture_array()
        if FLIP_MODE is not None:
            frame = cv2.flip(frame, FLIP_MODE)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # 1. Create a copy and draw the green ROI crop box
        overlay_frame = frame_bgr.copy()
        cv2.rectangle(
            overlay_frame, 
            (ROI_LEFT, ROI_TOP), 
            (ROI_RIGHT, ROI_BOTTOM), 
            (0, 255, 0), # Green color in BBR
            2 # Thickness
        )
        # Add labels to the overlay
        cv2.putText(overlay_frame, "FULL FRAME (Green = Crop Area)", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 2. Extract the cropped ROI region
        cropped_roi = frame_bgr[ROI_TOP:ROI_BOTTOM, ROI_LEFT:ROI_RIGHT]
        
        # Resize cropped frame height to match the main frame for side-by-side display
        h, w, _ = cropped_roi.shape
        scale = FRAME_H / h
        cropped_resized = cv2.resize(cropped_roi, (int(w * scale), FRAME_H))
        cv2.putText(cropped_resized, "CROPPED VIEW (State Machine Sees)", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # 3. Stack them side-by-side
        combined = np.hstack((overlay_frame, cropped_resized))

        # Encode frame to JPEG
        _, jpeg = cv2.imencode('.jpg', combined)
        return jpeg.tobytes()

    def close(self):
        self.picam2.stop()


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
                <title>WRO 2026 Camera ROI Tuner</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background: #1e1e1e;
                        color: #ffffff;
                        text-align: center;
                        margin: 0;
                        padding: 20px;
                    }
                    h1 { color: #00ff66; }
                    .container { margin-top: 20px; }
                    img {
                        border: 4px solid #333;
                        border-radius: 8px;
                        max-width: 100%;
                    }
                    .info {
                        margin-top: 15px;
                        color: #aaa;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <h1>WRO 2026 Camera ROI Tuner</h1>
                <p>Verify that your camera's vertical pitch/angle aligns the track within the green box.</p>
                <div class="container">
                    <img src="/stream.mjpg" />
                </div>
                <div class="info">
                    ROI Parameters: Top={top} | Bottom={bottom} | Left={left} | Right={right}
                </div>
            </body>
            </html>
            """.replace("{top}", str(ROI_TOP))\
               .replace("{bottom}", str(ROI_BOTTOM))\
               .replace("{left}", str(ROI_LEFT))\
               .replace("{right}", str(ROI_RIGHT))
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
                    time.sleep(0.05) # ~20 FPS limit to save bandwidth/CPU
            except Exception as e:
                logging.info(f"Client disconnected: {e}")

        else:
            self.send_error(404)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    # Initialize the camera streamer globally
    streamer = CameraStreamer()
    server_address = ('', 8000)
    
    try:
        server = ThreadedHTTPServer(server_address, StreamingHandler)
        logging.info("=========================================")
        logging.info(" ROI Web Server running on port 8000")
        logging.info(" Open: http://<your_pi_ip_address>:8000")
        logging.info(" Press Ctrl+C to stop.")
        logging.info("=========================================")
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stopping web server...")
    finally:
        streamer.close()
