"""
servo_test_server.py

A simple web-based calibration tool run directly on your laptop (Windows).
Connect your ESP32-S3 directly to your laptop via USB, run this script, and
open http://localhost:8080 in your browser.

Provides a GUI slider and buttons to test your MG996R servo's limits
(left, right, center) to find the exact mechanical binding bounds.

Uses the same serial protocol: "S<angle>,0\n"
No need to modify or re-flash the ESP32!
"""

import sys
import os
import time
import logging
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading

import serial
import serial.tools.list_ports

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

PORT = 8080

class LaptopSerialLink:
    def __init__(self, baud=115200):
        self.baud = baud
        self._ser = None
        self._connected = False
        self.port_name = None

    def auto_connect(self):
        """Scan for available COM ports on Windows and try to open one."""
        if self._connected:
            return True

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            logging.warning("No COM ports found. Is the ESP32 plugged into the laptop?")
            return False

        # Try to find a port (preferring USB-serial chips)
        candidates = []
        for p in ports:
            logging.info(f"Found port: {p.device} - {p.description}")
            candidates.append(p.device)

        # Try connecting to the first available candidate
        for port in candidates:
            try:
                logging.info(f"Attempting to connect to {port}...")
                self._ser = serial.Serial(port, self.baud, timeout=0.1)
                time.sleep(2.0) # Settle connection (ESP32-S3 resets on connect)
                self.port_name = port
                self._connected = True
                logging.info(f"Successfully connected to ESP32 on {port}!")
                return True
            except Exception as e:
                logging.error(f"Failed to connect to {port}: {e}")
                self._ser = None
                self._connected = False
        return False

    def send_angle(self, angle):
        if not self._connected:
            if not self.auto_connect():
                return False
        
        try:
            command = f"S{int(angle)},0\n"
            self._ser.write(command.encode('ascii'))
            logging.info(f"Sent command: {command.strip()} to {self.port_name}")
            return True
        except Exception as e:
            logging.error(f"Serial write error: {e}")
            self._connected = False
            if self._ser:
                self._ser.close()
            return False

    def close(self):
        if self._ser:
            self._ser.close()

class TestServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute standard GET requests logging to keep terminal clean
        return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == '/set_angle':
            # Handle angle updates from the browser GUI
            query = urllib.parse.parse_qs(parsed_url.query)
            if 'val' in query:
                angle = int(query['val'][0])
                success = serial_link.send_angle(angle)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                status_str = "Connected" if success else "Disconnected (Check USB)"
                self.wfile.write(f'{{"status": "{status_str}", "port": "{serial_link.port_name}"}}'.encode('utf-8'))
                return

        # Main Landing Page
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # HTML + Javascript Interface
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MG996R Steering Calibration Tool</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #1a1a24;
                    color: #e2e2e7;
                    text-align: center;
                    margin: 0;
                    padding: 20px;
                }
                .card {
                    background: #242432;
                    max-width: 500px;
                    margin: 40px auto;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                }
                h1 { color: #00ff88; margin-bottom: 5px; }
                .subtitle { color: #8a8a9e; font-size: 14px; margin-bottom: 25px; }
                .status-box {
                    background: #2f2f42;
                    padding: 10px;
                    border-radius: 6px;
                    margin-bottom: 20px;
                    font-weight: bold;
                }
                .status-val { color: #ff3366; }
                .status-val.connected { color: #00ff88; }
                .angle-display {
                    font-size: 64px;
                    font-weight: bold;
                    color: #00e1ff;
                    margin: 20px 0;
                }
                input[type=range] {
                    width: 100%;
                    margin: 20px 0;
                    accent-color: #00ff88;
                }
                .btn-group {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 10px;
                    margin-top: 15px;
                }
                button {
                    background: #3a3a52;
                    border: none;
                    color: white;
                    padding: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                button:hover { background: #4e4e6e; }
                button.preset { background: #00aaff; }
                button.preset:hover { background: #00c3ff; }
                .limits-info {
                    margin-top: 25px;
                    font-size: 13px;
                    color: #8a8a9e;
                    text-align: left;
                    background: #2a2a3a;
                    padding: 15px;
                    border-radius: 6px;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>MG996R Calibration</h1>
                <div class="subtitle">WRO 2026 Laptop Steering Calibrator</div>
                
                <div class="status-box">
                    ESP32 Status: <span id="status" class="status-val">Scanning...</span>
                    <br>
                    <span id="port-info" style="font-size:12px; font-weight:normal; color:#8a8a9e;"></span>
                </div>

                <div class="angle-display"><span id="angle-val">90</span>&deg;</div>
                
                <input type="range" id="angle-slider" min="0" max="180" value="90" oninput="updateAngle(this.value)" />

                <div class="btn-group">
                    <button onclick="adjustAngle(-5)">-5&deg;</button>
                    <button onclick="adjustAngle(-1)">-1&deg;</button>
                    <button onclick="adjustAngle(1)">+1&deg;</button>
                    <button onclick="adjustAngle(5)">+5&deg;</button>
                </div>

                <div class="btn-group" style="grid-template-columns: repeat(3, 1fr); margin-top: 10px;">
                    <button class="preset" onclick="setPreset(60)">LEFT (60&deg;)</button>
                    <button class="preset" onclick="setPreset(90)" style="background:#00ff88; color:#121212;">CENTER (90&deg;)</button>
                    <button class="preset" onclick="setPreset(120)">RIGHT (120&deg;)</button>
                </div>

                <div class="limits-info">
                    <strong>Tuning Steps:</strong>
                    <ol style="margin: 5px 0 0 15px; padding: 0;">
                        <li>Slowly slide towards Left/Right presets.</li>
                        <li>Watch the wheels. If they stop turning but the servo buzzes, you hit the limit!</li>
                        <li>Record the limits to update <code>STEER_MAX_LEFT</code> and <code>STEER_MAX_RIGHT</code> in your code.</li>
                    </ol>
                </div>
            </div>

            <script>
                const slider = document.getElementById('angle-slider');
                const display = document.getElementById('angle-val');
                const statusSpan = document.getElementById('status');
                const portSpan = document.getElementById('port-info');

                let debounceTimer;

                function updateAngle(val) {
                    display.innerText = val;
                    slider.value = val;
                    
                    // Send value to server
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        fetch('/set_angle?val=' + val)
                            .then(response => response.json())
                            .then(data => {
                                statusSpan.innerText = data.status;
                                if (data.status === "Connected") {
                                    statusSpan.className = "status-val connected";
                                    portSpan.innerText = "Port: " + data.port;
                                } else {
                                    statusSpan.className = "status-val";
                                    portSpan.innerText = "";
                                }
                            });
                    }, 20);
                }

                function adjustAngle(diff) {
                    let newVal = parseInt(slider.value) + diff;
                    newVal = Math.max(0, Math.min(180, newVal));
                    updateAngle(newVal);
                }

                function setPreset(val) {
                    updateAngle(val);
                }

                // Initial connection trigger
                updateAngle(90);
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    serial_link = LaptopSerialLink()
    
    # Run first attempt to connect to ESP32
    serial_link.auto_connect()

    server_address = ('', PORT)
    try:
        server = ThreadedHTTPServer(server_address, TestServerHandler)
        logging.info("==================================================")
        logging.info(f" Laptop Calibration Server running on port {PORT}")
        logging.info(f" Open: http://localhost:{PORT}")
        logging.info(" Connect the ESP32 directly to your laptop via USB!")
        logging.info(" Press Ctrl+C to stop.")
        logging.info("==================================================")
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stopping calibration server...")
    finally:
        serial_link.close()
