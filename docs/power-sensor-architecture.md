# Power & Sensor Architecture - WRO 2026 Future Engineers

This document details the power delivery system, electrical connections, sensor integration, and wiring diagram of the autonomous vehicle.

---

## ⚡ Power Supply & Regulation

The vehicle is powered by a central **12V Battery** (e.g., LiPo or NiMH). Since different components require different operating voltages, two DC-to-DC step-down buck converters are used:

```
                  ┌───► [12V to 6V Regulator] ───► MG996R Servo Motor (6V)
                  │
[12V Battery] ────┼───► [12V to 5V Regulator] ───► ESP32-S3 Dev Board (5V USB/VIN)
                  │
                  ├───► [H-Bridge/DRV8833] ──────► 12V DC Drive Motor
                  │
                  └───► [USB Power Bank/Batt] ───► Raspberry Pi 4B (5V)
```

### Voltage Distribution Details:
1. **12V Rail**: Powers the rear drive DC motor through the DRV8833 H-bridge.
2. **6V Rail (12V-to-6V Converter)**: Dedicated to powering the **MG996R Servo Motor**. Stepping down to 6V provides the optimal torque and speed for Ackerman steering without exceeding the servo's maximum voltage.
3. **5V Rail (12V-to-5V Converter)**: Powers the **ESP32-S3 Dev Board** logic circuitry.
4. **Raspberry Pi Power**: Powered by a separate dedicated 5V USB-C supply (or high-amperage converter) to ensure the computer does not brown out during motor accelerations.

---

## 🔌 Pin Connections & Protocols

### 1. Raspberry Pi 4B Connections
| Device / Sensor | Connection Protocol | Physical Port | Details |
| :--- | :--- | :--- | :--- |
| **D500 Lidar** | UART | `/dev/serial0` | RX/TX GPIO pins, 230400 Baud |
| **ESP32-S3 Dev Board**| USB Serial | `/dev/ttyUSB0` | USB-A to USB-C cable, 115200 Baud |
| **Pi Camera Rev 1.3** | CSI Interface | Camera Ribbon Port | Native libcamera interface |

### 2. ESP32-S3 Dev Board Connections
| Device / Actuator | Connection Protocol | ESP32 GPIO Pin | Details |
| :--- | :--- | :--- | :--- |
| **MG996R Servo (Signal)** | PWM (50Hz) | **GPIO 18** | Controlled via ESP32Servo library |
| **DRV8833 AIN1** | PWM | **GPIO 4** | Drive Motor Speed / Direction A |
| **DRV8833 AIN2** | PWM | **GPIO 5** | Drive Motor Speed / Direction B |

---

## ⚠️ Electrical Grounding (Common GND)

To prevent signal noise, voltage floating, or burning out components:
* **The ground loops must be completed**: The negative (-) terminal of the 12V battery, the GND of the ESP32-S3, the GND of the DC-to-DC converters, and the GND of the Raspberry Pi **must all be connected together**.
* **Failure to connect these grounds will cause the MG996R servo to twitch erratically or destroy the ESP32 input protection diodes.**
