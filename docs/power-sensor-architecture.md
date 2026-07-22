# Power & Sensor Architecture - WRO 2026 Future Engineers

This document details the electrical power distribution, voltage domains, sensor suite selection, and the critical design decisions made to protect our hardware.

---

## ⚡ Power Domains & Voltage Regulation

The robot operates on three distinct voltage domains to support logic processing, high-torque servo steering, and motor drive:

```
                  ┌───► [12V-to-6V Buck Converter] ───► MG996R Servo (6V)
                  │
[12V Battery] ────┼───► [12V-to-5V Buck Converter] ───► ESP32-S3 Logic (5V)
                  │
                  └───► [DRV8833 Motor Driver] ──────► 12V DC Motor (Voltage Regulated)
                  
[USB Power Bank] ────────────────────────────────────► Raspberry Pi 4B (5V / 3A)
```

### 1. Raspberry Pi 4B (5V / 3A)
- **Power Source**: Dedicated external 5V/3A USB-C Power Bank.
- **Reasoning**: The Raspberry Pi 4B is highly sensitive to voltage drops. If the Pi shared a battery with the heavy DC drive motor, the sudden current draw when the motor starts would drop the battery voltage (brownout), causing the Pi to crash or reboot. A completely isolated power bank guarantees stable perception and control processing.

### 2. MG996R Servo Motor (6V Rail)
- **Power Source**: 12V Battery stepped down to **6V** using a dedicated high-current DC-to-DC buck converter.
- **Reasoning**: The MG996R steering servo operates between 4.8V and 7.2V. At 4.8V, it lacks the torque to turn the front wheels quickly at speed. At 6.0V, it provides **10 kg-cm of torque** and a transit time of 0.15s per 60 degrees. A dedicated 6V converter protects the servo from the 12V battery voltage while maximizing its steering response.

### 3. ESP32-S3 Dev Board (5V Rail)
- **Power Source**: 12V Battery stepped down to **5V** using a 12V-to-5V DC-to-DC buck converter.
- **Reasoning**: Provides a clean, regulated 5V source to the ESP32's VIN pin.

---

## ⚠️ The DRV8833 10.8V Maximum Voltage Concern

### The Problem:
Our drive system uses a 12V DC motor, and we are using a **DRV8833 Dual H-Bridge driver**. 
- According to the Texas Instruments datasheet, the **maximum operating voltage of the DRV8833 is 10.8V**.
- A fully charged 3S LiPo battery (11.1V nominal) reaches **12.6V**, which exceeds the absolute maximum ratings of the DRV8833 and will permanently burn out the driver's internal MOSFETs.

### The Resolution:
To resolve this voltage mismatch and protect the DRV8833, we implemented the following design constraint:
* **Option A (Voltage Regulation)**: The motor power rail input of the DRV8833 is regulated down to a safe **9V** using a heavy-duty buck regulator. This limits the peak voltage to the driver and ensures it never runs hot.
* **Option B (Battery Selection)**: Alternatively, we can run the drive train on a **2S LiPo battery (7.4V nominal, 8.4V max)** or an **8.4V NiMH battery pack**. This fits completely within the DRV8833's safe operating envelope, though it slightly reduces the top speed of the 12V DC motor.

---

## 🛰️ Sensor Suite Selection & Placement Reasoning

To satisfy WRO rules and safely navigate the track, our sensor suite consists of a Lidar and a Camera. **We did not use any Time-of-Flight (ToF) sensors.**

```
       [Pi Camera Rev 1.3] (Rear-facing, angled down)
              │
              ▼ (Captures 60px slice of floor for color)
              
       [D500 LiDAR] (Top-mounted, flat)
              │
              ▼ (360° distance mapping of walls)
```

### 1. D500 LiDAR (perception of walls and obstacles)
- **Placement**: Mounted flat on the highest tier of the chassis, centered relative to the axles.
- **Reasoning**: A 360-degree rangefinder. By placing it on top, it has an unobstructed view of the surrounding walls and pillars, allowing the code to calculate wall distances at 90° (left) and 270° (right) for auto-centering.

### 2. Raspberry Pi Camera Rev 1.3 (perception of color signs)
- **Placement**: Mounted backwards (rear-facing) and upside-down on the chassis, angled downwards at a fixed pitch.
- **Reasoning**: Used strictly to detect the color of upcoming pillars. By mounting it pointing backwards, we can read colors after passing them, or focus on objects behind us. Flipped 180° in software (`FLIP_MODE = -1`) to correct the physical upside-down mounting.

### 3. Why we did NOT use Time-of-Flight (ToF) Sensors:
- **Reduced Bus Congestion**: Multiple ToF sensors require sharing the I2C bus. On a Raspberry Pi, managing multiple I2C addresses (like VL53L1X sensors) requires complex XSHUT pin-addressing code and increases latency.
- **Simplified Software Architecture**: The D500 Lidar already provides a complete 360° distance profile. Adding ToF sensors would create redundant data that would slow down the core state machine.
- **Reduced Weight and Wiring**: Eliminating extra sensor breakout boards and wiring harnesses simplifies the chassis design and reduces electrical failure points.
