# Power & Sensor Architecture - WRO 2026 Future Engineers

This document details the electrical power distribution, voltage domains, system power budget, sensor suite selection, and the critical design decisions made to protect our hardware.

---

## ⚡ Power Domains & Voltage Regulation

Our autonomous vehicle runs a high-draw electrical system. To support these demands stably and prevent voltage sags from affecting processing logic, the power distribution is split across dedicated regulators:

```
                  ┌───► [12V-to-6V Buck Converter] ───► MG996R Servo (6V)
                  │
[12V Battery] ────┼───► [12V-to-5V Buck Converter] ───► Raspberry Pi 4B & ESP32-S3 (5V)
(2P3S Samsung)    │
                  └───► [A4950 Motor Driver] ─────────► 37mm DC Motor (12V)
```

---

## 📊 System Power Budget & Battery Life Calculations

To ensure that the power supply can sustain operating current without unexpected brownouts, we constructed a complete system power budget:

| Subsystem / Device | Operating Voltage | Nominal Current | Peak / Stall Current | Power (Nominal) |
| :--- | :--- | :--- | :--- | :--- |
| **Raspberry Pi 4B** | 5.0V | 1.2A | 2.5A | 6.0W |
| **ESP32-S3 Dev Board** | 5.0V | 0.15A | 0.3A | 0.75W |
| **D500 Lidar** | 5.0V | 0.2A | 0.4A | 1.0W |
| **Pi Camera Rev 1.3** | 3.3V (via Pi) | 0.15A | 0.25A | 0.5W |
| **MG996R Servo Motor** | 6.0V | 0.5A | 1.5A | 3.0W |
| **37mm DC Gearmotor** | 12.0V | 0.8A | 2.5A | 9.6W |
| **BMS Cooling Blower Fan**| 5.0V | 0.1A | 0.2A | 0.5W |
| **TOTAL** | -- | **3.1A (Avg)** | **7.65A (Peak)** | **21.35W (Avg)** |

### Battery Endurance Calculation:
- **Battery Capacity**: $6\text{Ah} = 6000\text{ mAh}$ (at 12V nominal).
- **Average Current Draw**: $I_{\text{avg}} \approx 1.8\text{A}$ from the 12V battery rail.
- **Estimated Continuous Operating Time ($t$)**:

  $$t = \frac{\text{Battery Capacity}}{\text{Average Current Draw}} = \frac{6.0\text{ Ah}}{1.8\text{ A}} \approx 3.33\text{ hours}$$

- **Safety Margin**: Operating at $50\%$ duty cycle provides over **1.5 hours of continuous track testing**, far exceeding the 3-minute competition run requirement.

---

## ❄️ Battery Management System (BMS) Thermal Management

* **The Problem**: During testing, we discovered that the BMS located inside the battery pack was heating up significantly and began melting through its housing, even with light usage.
* **The Constraint**: Since our Kodama Trinus printer only prints in PLA, we could not manufacture a heat-resistant enclosure (PLA begins softening and deforming at 60°C).
* **The Solution**: We moved the BMS to a separate location and designed a custom **5W blower fan cooling rig** to actively blow air across the BMS heatsink, keeping it cool and preventing thermal deformation.

---

## 🔌 Actuator & Sensor Interfaces

### 1. Raspberry Pi 4B Pinouts
| Device / Sensor | Connection Protocol | Physical Port / Pin | Details |
| :--- | :--- | :--- | :--- |
| **D500 Lidar (Data)** | UART | `/dev/serial0` (GPIO 14/15) | 230400 Baud |
| **D500 Lidar (PWM)** | Hardware PWM | **GPIO 12 (PWM0)** | 1kHz PWM motor speed control |
| **ESP32-S3 Board** | GPIO UART / USB | `/dev/ttyAMA1` or `/dev/ttyUSB0` | 115200 Baud command link |
| **Pi Camera Rev 1.3** | CSI Ribbon | Camera CSI Port | Native libcamera interface |

### 2. ESP32-S3 Pinouts
| Device / Actuator | Connection Protocol | ESP32 GPIO Pin | Details |
| :--- | :--- | :--- | :--- |
| **Motor Driver AIN1** | PWM Output | **GPIO 16** | Direction / Speed Input 1 |
| **Motor Driver AIN2** | PWM Output | **GPIO 17** | Direction / Speed Input 2 |
| **Motor Encoder C1** | Interrupt Input | **GPIO 32** | Encoder Phase 1 Signal |
| **Motor Encoder C2** | GPIO Input | **GPIO 33** | Encoder Phase 2 Signal |
| **MG996R Servo (Signal)** | PWM (50Hz) | **GPIO 18** | Controlled via ESP32Servo library |
| **Pi UART Connection** | Hardware Serial1 | **GPIO 4 (RX)** / **GPIO 5 (TX)** | Connects to Raspberry Pi TX/RX |


### 2. A4950 Motor Driver Choice
- **Reasoning**: We chose the **A4950 motor driver** to run the 37mm gearmotor. It supports the higher current requirements of our motor under load (up to 2.5A stall) and is compatible with the ESP32's PWM speed control.

---

## 🛰️ Sensor Placement & Field Geometry Rationale

To satisfy WRO rules and safely navigate the track, our sensor suite consists of a Lidar and a Camera. **We did not use any Time-of-Flight (ToF) sensors.**

### 1. D500 LiDAR (perception of walls and obstacles)
- **Placement**: Mounted flat on the front of the vehicle, directly behind the steering servo.
- **Reasoning**: Placed at the front to guarantee that its forward-facing 180° sweep is completely unobstructed, allowing the vehicle to detect walls and obstacles ahead.

### 2. Raspberry Pi Camera Rev 1.3 (perception of color signs)
- **Placement**: Mounted on an elevated platform directly above the Lidar, angled slightly downwards.
- **Field Geometry Calculation**: The camera is mounted at a height of $h = 16\text{ cm}$ and tilted downwards at an angle of $\theta = 35^\circ$. The 60-pixel vertical crop slice ($y = 190$ to $250$) projects to a ground distance of $d \approx 25\text{ cm}$ to $40\text{ cm}$ ahead of the front bumper. This geometry gives the State Machine exactly $300\text{ ms}$ to initiate a turn before the car reaches the pillar.

### 3. Why we did NOT use Time-of-Flight (ToF) Sensors:
- **Color Sensitivity Issues**: During early prototyping, we found that ToF sensors struggled to detect distances to the **black walls** of the WRO arena. Lidar, using laser technology, easily overcomes material and color reflections to deliver accurate distance profiles.
- **Stacked Layout Efficiency**: By stacking the Lidar and camera vertically at the front of the car, we saved physical space, allowed better airflow to the boards, and simplified the software.

![Stacked Lidar and Camera Physical Layout](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/media/robot-photos/robot_front.jpeg)

---

## 🛡️ Failure-Point Considerations & Mitigation

1. **Serial Link Disconnection**: If the USB serial cable between the Pi 4B and ESP32-S3 is disconnected mid-run, `serial_link.py` detects the drop within 30ms and triggers `emergency_stop()`. The ESP32 firmware watchdog cuts motor power if no command is received for 500ms.
2. **Reverse Voltage Protection**: Reverse polarity protection diodes are placed on the input of the buck converters to prevent accidental battery reversal from destroying the logic ICs.
3. **Common Ground**: All negative rails (Battery -, ESP32 GND, Pi GND, Buck GND) are tied together to eliminate floating potential voltage spikes.
