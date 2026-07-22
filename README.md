# WRO 2026 Future Engineers: Autonomous Self-Driving Car

This repository contains the complete autonomous driving software stack and hardware documentation for our self-driving car competing in the **WRO 2026 Future Engineers** competition.

---

## 📂 Repository Structure

```
WRO-Competition/
├── README.md                 # Project Overview
├── requirements.txt          # Python dependencies
├── struct.txt                # Directory tree layout
├── main.py                   # Raspberry Pi main thread coordinator
│
├── docs/                     # Technical documentation reports
│   ├── mechanical-design.md
│   ├── power-sensor-architecture.md
│   ├── software-architecture.md
│   └── engineering-journal.md
│
├── control/                  # Decision logic & communication
│   ├── __init__.py
│   ├── state_machine.py      # Wall-following & obstacle avoidance engine
│   └── serial_link.py        # USB Serial link to ESP32 (S<angle>,<speed>\n)
│
├── lidar/                    # Lidar sensing
│   ├── __init__.py
│   └── lidar_reader.py       # D500 Lidar serial packet parser
│
├── vision/                   # Camera sensing
│   ├── __init__.py
│   └── camera_vision.py      # OpenCV color masking, flipping, and ROI crop
│
├── firmware/                 # Actuator firmware
│   ├── esp32_firmware/       # Core microcontroller firmware (DRV8833 & Servo)
│   └── servo_web_calibration/# C++ Web Server calibrator sketch
│
├── calibration/              # Visual and sensor calibration tools
│   ├── hsv_tune.py           # OpenCV trackbar tuner for HSV thresholds
│   ├── web_tuner.py          # HTTP live camera crop visualizer
│   └── lidar_plot.py         # HTTP 2D live radar plotter (1m range)
│
├── cad/                      # Chassis 3D files & renders
│   ├── chassis/
│   └── renders/
│
└── media/                    # Diagrams, schematics & builds photos
    ├── robot-photos/
    ├── wiring/
    └── diagrams/
```

---

## ⚙️ How to Run the System on the Raspberry Pi

1. **Activate Virtual Environment**:
   ```bash
   source venv/bin/activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Execute Main Engine**:
   ```bash
   python3 main.py
   ```

---

## 🛠️ Calibration Utilities

* **Camera ROI Slice Visualizer (Port 8000)**:
  `python calibration/web_tuner.py`
  *(View crop slice live at http://<pi_ip>:8000)*
* **Lidar 2D Radar Map (Port 8001)**:
  `python calibration/lidar_plot.py`
  *(View radar sweep live at http://<pi_ip>:8001)*
* **ESP32 Steering Calibrator (Wi-Fi AP)**:
  Connect to Wi-Fi SSID `ESP32-Servo-Calibrator` (Password: `password123`) and open `http://192.168.4.1` on your device.
