"""
main.py

The main entry point for the WRO 2026 self-driving car on Raspberry Pi.
Initializes sensor and control threads, handles graceful shutdown on SIGINT/Ctrl+C.

Usage on Raspberry Pi:
    python main.py
"""

import time
import signal
import sys
import logging

from vision.camera_vision import CameraVision
from lidar.lidar_reader import LidarReader
from control.serial_link import SerialLink
from control.state_machine import StateMachine

# Configure logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def main():
    logging.info("==========================================")
    logging.info("  Starting WRO 2026 Autonomous Car System ")
    logging.info("==========================================")

    # 1. Initialize sensor and communication instances
    # Adjust ports if using USB-to-Serial adapters for Lidar
    vision = CameraVision(frame_w=640, frame_h=480)
    lidar = LidarReader(port="/dev/serial0", baud=230400) 
    serial_link = SerialLink(port="/dev/ttyUSB0", baud=115200, auto_detect=True)
    
    # 2. Instantiate state machine controller
    sm = StateMachine(vision=vision, lidar=lidar, serial_link=serial_link, loop_hz=20)

    # 3. Clean signal handling for Ctrl+C
    def signal_handler(sig, frame):
        logging.info("\nShutdown signal received. Stopping all threads...")
        sm.stop()
        vision.stop()
        lidar.stop()
        serial_link.stop()
        logging.info("All threads safely stopped. Goodbye.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start background threads
        logging.info("Starting SerialLink thread...")
        serial_link.start()
        
        logging.info("Starting LidarReader thread...")
        lidar.start()
        
        logging.info("Starting CameraVision thread...")
        vision.start()
        
        # Let sensors warm up & buffer data
        time.sleep(1.5)

        # Run control loop (blocking call until stopped)
        logging.info("Starting StateMachine control loop...")
        sm.start()

    except Exception as e:
        logging.critical("Fatal error encountered in main execution: %s", e, exc_info=True)
    finally:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
