# WRO 2026 Future Engineers: Autonomous Self-Driving Car

This repository contains the complete autonomous driving software stack, calibration utilities, and engineering documentation for our self-driving car competing in the **WRO 2026 Future Engineers** competition.

Our design centers around a **two-brain architecture**: a high-level **Raspberry Pi 4B** for computer vision and Lidar processing, and a low-level **ESP32-S3 Dev Board** to drive the Ackerman steering servo and DC motor driver.

---

## 📸 Project Overview & Team Information

Our team has designed and built a scale autonomous vehicle capable of:
1. **Centering itself** inside the lanes of the track using a high-frequency Proportional-Derivative (PD) controller reading Lidar walls.
2. **Detecting color markers** (red and green pillars) using a Pi Camera, and performing obstacle avoidance maneuvers according to the game rules.
3. **Navigating the track** for 3 complete laps, tracking checkpoints, and performing a controlled stop/parking sequence at the finish line.

---

## 🛠️ Hardware Component List & Specifications

To ensure reliability, speed, and safety, we selected the following hardware components:

| Component | Role | Selection Rationale |
| :--- | :--- | :--- |
| **Raspberry Pi 4B** | High-Level Brain | Handles the operating system, multithreaded Python scripts, OpenCV color masking, and Lidar data parsing. Chosen for its quad-core processing power and high compatibility with Picamera2 and serial links. |
| **D500 Lidar** | Distance Sensor | Provides a high-speed, 360-degree polar map of distances to surrounding walls at 230400 baud. It replaced redundant ToF sensors, simplifying wire harnesses and logic. |
| **Pi Camera Rev 1.3** | Color Vision Sensor | Captures real-time track frames. Mounted backwards/upside-down on the chassis and cropped to a 60-pixel slice (`y = 190` to `250`) to focus on the track floor and ignore overhead lighting noise. |
| **ESP32-S3 Dev Board** | Actuator Driver | Executes low-level motor driver outputs and steering servo sweeps in C++. Chosen for its native hardware PWM timers, built-in Wi-Fi (for calibration web hosting), and fast hardware interrupts. |
| **DRV8833 H-Bridge** | Motor Driver | Controls the speed and direction of the drive motor. Its voltage limits are carefully managed (or stepped down to 9V) to avoid damage when running off the main 12V battery. |
| **MG996R Servo** | Steering Motor | High-torque metal-gear servo used to actuate the front Ackermann steering linkages. Metal gears prevent stripped teeth during crashes. Powered directly at 6V. |
| **12V DC Motor** | Drivetrain Motor | Powers the rear wheels through a mechanical differential gear system to ensure smooth turns without tire slippage. |
| **12V-to-6V Converter**| Power Regulation | High-current buck converter that steps down the main 12V battery to a stable 6V to power the MG996R servo at peak torque. |
| **12V-to-5V Converter**| Power Regulation | Buck converter that steps down the 12V battery to 5V to power the ESP32-S3 Dev Board logic. |

---

## 📂 Repository Structure & Documentation Directory

Here is the directory tree layout of the project. Click the links to access the specific engineering reports:

* **[docs/mechanical-design.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/mechanical-design.md)**: Details the mechanical calculations, Ackermann steering linkages, rear differential gear assembly, and chassis weight distribution.
* **[docs/power-sensor-architecture.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/power-sensor-architecture.md)**: Explains the electrical schematics, the 12V power domains, the DRV8833 10.8V maximum safety concern, and the common-grounding layout.
* **[docs/software-architecture.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/software-architecture.md)**: Explains the multi-threaded Python loops on the Pi 4B, the C++ web server code on the ESP32, the 6-state machine, and the PD centering algorithms.
* **[docs/engineering-journal.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/engineering-journal.md)**: A complete, chronological log of our design iterations, failures, and how we resolved them during testing.

```
wro2026/
├── README.md                 # This overview document
├── requirements.txt          # Python packages list (pyserial, numpy)
├── struct.txt                # Directory tree layout
├── main.py                   # Raspberry Pi main thread coordinator
│
├── control/                  # Decision logic & communication
│   ├── __init__.py
│   ├── state_machine.py      # Core 6-state driving logic (PD centering)
│   └── serial_link.py        # USB Serial transmission to ESP32
│
├── lidar/                    # Lidar sensing
│   ├── __init__.py
│   └── lidar_reader.py       # D500 Lidar serial packet parser
│
├── vision/                   # Camera sensing
│   ├── __init__.py
│   └── camera_vision.py      # OpenCV color masking and ROI crop
│
├── firmware/                 # Microcontroller code
│   ├── esp32_firmware/       # Production C++ sketch for DRV8833 & Servo
│   └── servo_web_calibration/# C++ Web Server steering limits tuner
│
└── calibration/              # Calibration utilities
    ├── hsv_tune.py           # OpenCV trackbar tuner for HSV thresholds
    ├── web_tuner.py          # HTTP live camera crop visualizer (Port 8000)
    └── lidar_plot.py         # HTTP 2D live radar plotter (Port 8001)
```

---

## ⚡ Quick Setup & Running Guide

### 1. Preparing the Raspberry Pi 4B
Ensure you are in the project root directory and your Python virtual environment is active:
```bash
# Navigate to project root
cd ~/wro2026

# Activate the virtual environment
source venv/bin/activate

# Install dependencies (pyserial, numpy)
pip install -r requirements.txt
```

### 2. Flashing the ESP32-S3
Open the Arduino IDE on your laptop, select the `ESP32S3 Dev Module` board, and upload the sketch:
* **Production Board**: Upload **`firmware/esp32_firmware/esp32_firmware.ino`**
* **Calibration Test Board**: Upload **`firmware/servo_web_calibration/servo_web_calibration.ino`**

### 3. Launching the System
Plug the ESP32-S3 and the Lidar into the Pi's USB/Serial ports, then run:
```bash
python3 main.py
```

---

## 🔧 Calibration Web Servers

To simplify calibration next to the physical track, the code features lightweight HTTP servers that stream visual feedback directly to your phone or laptop.

### 1. Camera Crop ROI Visualizer (Port 8000)
Run this command to check where the camera is cropping the track floor:
```bash
python calibration/web_tuner.py
```
Open your phone or laptop browser at: `http://bashar.local:8000` to see the full frame and the cropped slice side-by-side.

### 2. Lidar 2D Radar Map (Port 8001)
Run this command to check the 2D rangefinder points:
```bash
python calibration/lidar_plot.py
```
Open your browser at: `http://bashar.local:8001` to view a live 1-meter polar radar sweep showing the location of walls and obstacles.
