# WRO 2026 Future Engineers: Autonomous Self-Driving Car

This repository contains the complete autonomous driving software stack, calibration utilities, 3D printing files, and technical engineering documentation for our self-driving vehicle competing in the **WRO 2026 Future Engineers** competition.

Our design centers around a **two-brain architecture**: a high-level **Raspberry Pi 4B** for computer vision and Lidar perception, and a low-level **ESP32-S3 Dev Board** to drive the Ackerman steering servo and DC motor driver.

---

## 📸 Project Overview & Team Information

Our team has designed and built a scale autonomous vehicle capable of:
1. **Centering itself** inside the lanes of the track using a high-frequency Proportional-Derivative (PD) controller reading 360° Lidar walls.
2. **Detecting color markers** (red and green pillars) using a Pi Camera Rev 1.3, and performing obstacle avoidance maneuvers according to the WRO game rules (steer left for red pillars, steer right for green pillars).
3. **Navigating the track** for 3 complete laps, tracking checkpoints, and performing a controlled stop/parking sequence at the finish line.

---

## ⚙️ Hardware Component List & Specifications

To ensure reliability, high-speed perception, and mechanical safety, we selected the following hardware components:

| Component | Role | Selection Rationale & Specs |
| :--- | :--- | :--- |
| **Raspberry Pi 4B** | High-Level Brain | Handles the operating system, multithreaded Python 3 scripts, OpenCV color masking, and Lidar data parsing. Chosen for its quad-core processing power and native libcamera interface. |
| **D500 Lidar** | Distance Sensor | Provides a high-speed, 360-degree polar map of distances to surrounding walls at 230400 baud (up to 50Hz turn rate). Replaced ToF sensors due to superior reflection on black arena walls. |
| **Pi Camera Rev 1.3** | Color Vision Sensor | Captures real-time track frames. Mounted backwards/upside-down on the chassis and cropped to a 60-pixel slice (`y = 190` to `250`) to focus on the track floor and ignore overhead lighting noise. |
| **ESP32-S3 Dev Board** | Actuator Driver | Executes low-level motor driver outputs and steering servo sweeps in C++. Chosen for its native hardware PWM timers, built-in Wi-Fi (for web calibration), and fast hardware interrupts. |
| **A4950 H-Bridge** | Motor Driver | Drives the 37mm gearmotor. Chosen over DRV8833/L298N for its high current handling (up to 3.5A peak) and wide voltage tolerance (up to 40V). |
| **MG996R Servo** | Steering Motor | High-torque metal-gear servo used to actuate the front Ackermann steering linkages. Metal gears prevent stripped teeth during high-speed turns or wall impacts. Powered at 6V. |
| **37mm DC Gearmotor** | Drivetrain Motor | Powers the rear wheels through a mechanical differential gear system and belt drive (333 RPM max speed). |
| **12V 2P3S Battery** | Main Power Source | 12V 6Ah custom pack built with high-density Samsung lithium-ion cells. Paired with an active 5W blower fan cooling rig for the BMS. |
| **12V-to-6V Converter**| Power Regulation | High-current DC-to-DC buck converter stepping 12V down to 6.0V to power the MG996R servo at peak torque. |
| **12V-to-5V Converter**| Power Regulation | Step-down converter supplying clean 5V logic power to the ESP32-S3 Dev Board and Raspberry Pi 4B. |

---

## 📂 Repository Structure & Documentation Directory

Here is the complete directory tree layout of the project. Click the links to access the specific engineering reports:

* **[docs/mechanical-design.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/mechanical-design.md)**: Details the mechanical calculations, 3D printing constraints (Kodama Trinus $12\times12\text{ cm}$ bed), Ackermann steering linkages, rear differential gear assembly, speed/torque formulas, and chassis weight distribution.
* **[docs/power-sensor-architecture.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/power-sensor-architecture.md)**: Explains the electrical schematics, the 12V power domains, the complete system power budget table, battery endurance calculations, and the common-grounding layout.
* **[docs/software-architecture.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/software-architecture.md)**: Explains the multi-threaded Python loops on the Pi 4B, the C++ web server code on the ESP32, the 6-state machine diagram, performance metrics, and edge-case failure recovery algorithms.
* **[docs/engineering-journal.md](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/docs/engineering-journal.md)**: A complete, chronological log of our design iterations, failures, trade-offs, and risk identification & mitigation matrix.

```
wro2026/
├── README.md                 # Project Overview & Reproducibility Guide
├── requirements.txt          # Python packages list (pyserial, numpy)
├── struct.txt                # Directory tree layout
├── main.py                   # Raspberry Pi main thread coordinator
│
├── docs/                     # Technical documentation reports (WRO Rubric)
│   ├── mechanical-design.md
│   ├── power-sensor-architecture.md
│   ├── software-architecture.md
│   └── engineering-journal.md
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
│   ├── esp32_firmware/       # Production C++ sketch for A4950 & Servo
│   ├── servo_calibration/    # C++ Serial Monitor calibration sketch
│   └── servo_web_calibration/# C++ Web Server steering limits tuner
│
├── calibration/              # Calibration utilities
│   ├── hsv_tune.py           # OpenCV trackbar tuner for HSV thresholds
│   ├── web_tuner.py          # HTTP live camera crop visualizer (Port 8000)
│   └── lidar_plot.py         # HTTP 2D live radar plotter (Port 8001)
│
├── cad/                      # Chassis 3D files & renders
│   ├── chassis/
│   └── renders/              # CAD screenshot exports
│
└── media/                    # Diagrams, schematics & build photos
    ├── robot-photos/         # Physical photos of the build
    ├── wiring/               # Wiring schematics
    └── diagrams/             # System diagrams and flowcharts
```

---

## ⚡ Quick Setup & Reproducibility Guide

To reproduce our software setup on another Raspberry Pi 4B:

### 1. Preparing the Raspberry Pi 4B
Ensure you are in the project root directory and your Python virtual environment is active:
```bash
# Navigate to project root
cd ~/wro2026

# Create virtual environment (if new system)
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Flashing the ESP32-S3 Firmware
Open the Arduino IDE on your laptop, select the `ESP32S3 Dev Module` board, and upload the target sketch:
* **Production Driving Sketch**: Upload **`firmware/esp32_firmware/esp32_firmware.ino`**
* **Standalone Wi-Fi Calibrator**: Upload **`firmware/servo_web_calibration/servo_web_calibration.ino`**

### 3. Launching the System
Plug the ESP32-S3 and the Lidar into the Pi's USB/Serial ports, then execute:
```bash
python3 main.py
```

---

## 🔧 Live Calibration & Web Debugging Tools

To simplify field tuning next to the physical track without needing an attached monitor, our codebase includes lightweight HTTP streaming tools:

1. **Camera Crop ROI Visualizer (Port 8000)**:
   Run `python calibration/web_tuner.py` on the Pi, then open `http://bashar.local:8000` in your phone browser to see the full frame and cropped slice side-by-side.
2. **Lidar 2D Radar Map (Port 8001)**:
   Run `python calibration/lidar_plot.py` on the Pi, then open `http://bashar.local:8001` in your phone browser to view a live 1-meter polar radar sweep showing surrounding walls.
3. **ESP32 Steering Calibrator (Wi-Fi AP)**:
   Flash `servo_web_calibration.ino`, connect your phone to the Wi-Fi AP `ESP32-Servo-Calibrator` (Password: `password123`), and open `http://192.168.4.1` to test steering angles.

---

## 📜 Release Notes & Versioning

- **v1.0 (Production Release)**: Fully integrated multi-threaded perception, A4950 motor driver support, 180° camera flip, 60px ROI floor crop, 6-state machine, and web streaming diagnostic servers.
