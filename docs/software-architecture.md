# Software Architecture - WRO 2026 Future Engineers

This document details the software design, thread-based architecture, and logic controllers running on the Raspberry Pi 4B and the ESP32-S3.

---

## 🧵 Raspberry Pi Multi-Threaded Architecture

The Raspberry Pi 4B runs a multi-threaded Python 3 program to handle sensor input and control loops concurrently without blocking.

```
                    ┌─── CameraVision Thread (Pi Camera Rev 1.3 / BGR to HSV)
                    ├─── LidarReader Thread (D500 Lidar Serial / 230400 Baud)
  main.py (Loop) ───┤
                    ├─── StateMachine Controller (20Hz Engine / Decision Loop)
                    └─── SerialLink Thread (USB Serial to ESP32 / 115200 Baud)
```

### Thread Descriptions:
1. **CameraVision** (`vision/camera_vision.py`):
   - Grabs frames from **Pi Camera Rev 1.3**.
   - Rotates frame 180° (`FLIP_MODE = -1`) for backwards mounting.
   - Crops to a 60-pixel vertical slice (`y = 190` to `250`).
   - Converts to HSV, filters for Red/Green pillars, and extracts the largest contours.
2. **LidarReader** (`lidar/lidar_reader.py`):
   - Streams raw serial data from the **D500 Lidar** at 230400 baud.
   - Performs CRC8 checksum verification.
   - Populates a thread-safe map of distance measurements by degree (`0` to `359`).
3. **SerialLink** (`control/serial_link.py`):
   - Manages the USB-serial connection to the ESP32-S3.
   - Transmits steering and speed targets at a fixed 30Hz rate as ASCII string lines (`"S<angle>,<speed>\n"`).
4. **StateMachine** (`control/state_machine.py`):
   - The decision engine running at 20Hz.
   - Correlates camera detections and Lidar side distances to keep the car centered (using a P-controller) and steer around obstacles.

---

## 🔌 ESP32-S3 Microcontroller Firmware (C++)

The ESP32-S3 acts as the low-level hardware abstraction layer, receiving serial instructions from the Pi and translating them to PWM signals:

1. **Serial Listener**: Reads incoming `"S<angle>,<speed>\n"` packets.
2. **Servo Output**: Writes target angles (constrained between `60` and `120`) to the **MG996R servo** on GPIO 18 using the `ESP32Servo` library.
3. **Motor Output**: Writes speed PWM and direction signals to the DRV8833 motor driver pins (GPIO 4 & 5) to control the **12V DC motor**.
4. **Watchdog Timer**: Automatically cuts motor power if no command packet arrives from the Pi for 500ms.
