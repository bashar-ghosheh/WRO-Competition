# Mechanical Design - WRO 2026 Future Engineers

This document details the mechanical design, steering system, and drivetrain geometry of our autonomous self-driving car.

---

## 🏎️ Steering Geometry (Ackermann Steering)

The vehicle uses a standard **Ackermann steering mechanism** for the front wheels to ensure smooth cornering without tire slip.

```
       [Front Left Wheel]               [Front Right Wheel]
             \                                 /
              \---[Steering Linkage Joint]---/
                           |
                     [Servo Horn]
                           |
                 [MG996R Servo Motor]
```

### Steering Specifications:
- **Actuator**: MG996R High-Torque Metal Gear Servo.
- **Power Input**: Powered at **6V** via a dedicated 12V-to-6V DC-to-DC buck converter to achieve maximum holding torque and response speed.
- **Servo Center (Neutral)**: `90` (wheels pointing straight forward).
- **Steering Left Limit**: `60` (to avoid mechanical binding on the Ackermann linkages).
- **Steering Right Limit**: `120` (to avoid mechanical binding on the Ackermann linkages).

---

## ⚙️ Drivetrain

The rear-wheel-drive system is optimized for speed, traction, and cornering efficiency on the WRO track.

- **Drive Motor**: 12V DC Brushed Motor.
- **Differential**: Equipped with a **rear mechanical differential gear** to allow the outer wheel to spin faster than the inner wheel during cornering. This prevents wheel scrub and significantly improves turning radius and stability.
- **Motor Driver**: DRV8833 Dual H-Bridge driver.

---

## 📦 Component Layout & Weight Distribution

The physical placement of components is designed to keep the center of gravity low and centered:
1. **Low Level (Chassis Bed)**: 12V DC Motor, differential gear box, DRV8833, 12V-to-6V and 12V-to-5V buck converters, and the heavy 12V battery pack.
2. **Mid Level**: ESP32-S3 dev board and Raspberry Pi 4B.
3. **High Level**: D500 Lidar (mounted flat on top for an unobstructed 360° view) and the **Pi Camera Rev 1.3** (mounted pointing downwards/backwards at an angle to focus on the floor).
