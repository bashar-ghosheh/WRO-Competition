# Power & Sensor Architecture - WRO 2026 Future Engineers

This document details the electrical power distribution, voltage domains, sensor suite selection, and the critical design decisions made to protect our hardware.

---

## ⚡ Power Domains & Voltage Regulation

Our autonomous vehicle runs a high-draw electrical system. The drive motor under load can pull up to 2.5A at stall, and the Raspberry Pi 4B consumes up to 1.2A. To support these demands stably and prevent voltage sags from affecting processing logic, the power distribution is split across dedicated regulators:

```
                  ┌───► [12V-to-6V Buck Converter] ───► MG996R Servo (6V)
                  │
[12V Battery] ────┼───► [12V-to-5V Buck Converter] ───► Raspberry Pi 4B & ESP32-S3 (5V)
(2P3S Samsung)    │
                  └───► [A4950 Motor Driver] ─────────► 37mm DC Motor (12V)
```

![Power Distribution Block Diagram](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/media/diagrams/power_distribution.png)


### 1. The 12V 2P3S Battery Pack
- **Configuration**: Built using high-density **Samsung lithium-ion cells** wired in a **2P3S** (2 Parallel, 3 Series) configuration. This delivers a nominal **12V** with a high capacity of **6Ah**.
- **Reasoning**: A 2P3S pack provides a substantial energy pool, giving us plenty of headroom to absorb sudden voltage spikes from our actuators and protecting logic boards (Pi & ESP32) from severe voltage drops.

### 2. MG996R Servo Motor (6V Rail)
- **Power Source**: 12V Battery stepped down to **6V** using a dedicated high-current DC-to-DC buck converter.
- **Reasoning**: The MG996R steering servo operates best at 6V to deliver maximum torque and response time. A dedicated 6V converter protects the servo from the raw 12V battery line while ensuring consistent steering performance.

### 3. Logic Power (5V Rail)
- **Power Source**: 12V Battery stepped down to **5V** using a 12V-to-5V DC-to-DC buck converter.
- **Reasoning**: This clean 5V line supplies power to the Raspberry Pi 4B and the ESP32-S3 Dev Board, ensuring logic processing remains isolated from motor switching noise.

---

## ❄️ Battery Management System (BMS) Thermal Management

* **The Problem**: During testing, we discovered that the BMS located inside the battery pack was heating up significantly and began melting through its housing, even with light usage.
* **The Constraint**: Since our Kodama Trinus printer only prints in PLA, we could not manufacture a heat-resistant enclosure (PLA begins softening and deforming at 60°C).
* **The Solution**: We moved the BMS to a separate location and designed a custom **5W blower fan cooling rig** to actively blow air across the BMS heatsink, keeping it cool and preventing thermal deformation.

---

## 🔌 Actuator & Sensor Interfaces

### 1. Pin Connections & Protocols
| Source Device | Target Device | Protocol | Details |
| :--- | :--- | :--- | :--- |
| **Raspberry Pi 4B** | **ESP32-S3** | UART (USB Serial) | High-level coordinate stream (115200 baud) |
| **Raspberry Pi 4B** | **D500 Lidar** | UART | Raw polar distance sweeps |
| **Raspberry Pi 4B** | **Pi Camera Rev 1.3** | CSI Ribbon | High-speed video stream |
| **ESP32-S3** | **A4950 Motor Driver**| PWM + Direction | Controls the 37mm DC Motor speed and rotation |
| **ESP32-S3** | **MG996R Servo** | PWM | Steers the wheels (GPIO 18) |

### 2. A4950 Motor Driver Choice
- **Reasoning**: We chose the **A4950 motor driver** to run the 37mm gearmotor. It supports the higher current requirements of our motor under load (up to 2.5A stall) and is compatible with the ESP32's PWM speed control.

---

## 🛰️ Sensor Placement & Rationale

To satisfy WRO rules and safely navigate the track, our sensor suite consists of a Lidar and a Camera. **We did not use any Time-of-Flight (ToF) sensors.**

### 1. D500 LiDAR (perception of walls and obstacles)
- **Placement**: Mounted flat on the front of the vehicle, directly behind the steering servo.
- **Reasoning**: Placed at the front to guarantee that its forward-facing 180° sweep is completely unobstructed, allowing the vehicle to detect walls and obstacles ahead.

### 2. Raspberry Pi Camera Rev 1.3 (perception of color signs)
- **Placement**: Mounted on an elevated platform directly above the Lidar, angled slightly downwards.
- **Reasoning**: This vertical stacking layout keeps the camera's view of color pillars clear. Angling the camera down slightly minimizes image jitter during vehicle acceleration.

### 3. Why we did NOT use Time-of-Flight (ToF) Sensors:
- **Color Sensitivity Issues**: During early prototyping, we found that ToF sensors struggled to detect distances to the **black walls** of the WRO arena. Lidar, using laser technology, easily overcomes material and color reflections to deliver accurate distance profiles.
- **Stacked Layout Efficiency**: By stacking the Lidar and camera vertically at the front of the car, we saved physical space, allowed better airflow to the boards, and simplified the software.

![Stacked Lidar and Camera Physical Layout](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/media/robot-photos/robot_front.jpeg)


