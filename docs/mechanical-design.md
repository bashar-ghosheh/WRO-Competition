# Mechanical Design - WRO 2026 Future Engineers

This document details the mechanical design of our autonomous vehicle, explaining the engineering reasoning behind our chassis, steering geometry, and drivetrain selections.

---

## 🏎️ Chassis & Component Layout

The vehicle's physical chassis is designed with a two-tier structural layout to optimize the center of mass, ensure structural rigidity, and protect sensitive electronics from crashes.

```
┌────────────────────────────────────────────────────────┐
│  Upper Tier: D500 LiDAR (360° view) & Camera Rev 1.3  │
├────────────────────────────────────────────────────────┤
│  Middle Tier: Raspberry Pi 4B & ESP32-S3 Dev Board     │
├────────────────────────────────────────────────────────┤
│  Lower Tier: 12V Motor, Differential, Converters, Batt │
└────────────────────────────────────────────────────────┘
```

### Engineering Reasoning & Tradeoffs:
- **Material Selection**: Custom structural mounts and sensor brackets are fabricated using **3D printed PLA (Polylactic Acid)**. PLA was chosen because it allows for rapid prototyping iterations (crucial for modifying camera pitch angles and Lidar spacing) while maintaining sufficient rigidity to prevent sensor vibration.
- **Center of Gravity**: Heavy components (such as the 12V battery pack, the 12V DC drive motor, and the dual metal buck converters) are mounted as low as possible on the lower tier. This prevents the vehicle from tipping or rolling during high-speed, sharp evasive maneuvers around obstacles.

---

## 🔧 Steering Mechanism: Ackermann Geometry

Our steering utilizes **Ackermann geometry** to control the front wheels. 

```
   [Inside Wheel: turns sharper (30°)]       [Outside Wheel: turns wider (20°)]
                  \                                   /
                   \----[Ackermann Steering Link]----/
                                    |
                               [Servo Horn]
                                    |
                           [MG996R Servo Motor]
```

### Why Ackermann Geometry was Chose:
When a car turns, the inside wheel must follow a tighter circle than the outside wheel. If both wheels turned at the exact same angle (parallel steering), the tires would slip, lose traction, and cause the car to slide forward instead of turning. Ackermann geometry ensures that the steering linkages mechanically angle the inside wheel sharper than the outside wheel, reducing tire friction and allowing smooth, tight turns.

### Actuator Selection & Calibration:
- **MG996R Servo**: A high-torque metal-gear servo was selected. Standard plastic/nylon gear servos quickly strip their gears under the high lateral forces of steering at speed. The metal gears in the MG996R ensure durability during crashes.
- **Software Bounds Mapping**: To prevent the servo from forcing the wheels past their mechanical limits (which would stall the motor and burn out the servo controller), the software enforces strict boundaries:
  - **Neutral Center**: `90`
  - **Max Left Steering**: `60` (30° mechanical deflection)
  - **Max Right Steering**: `120` (30° mechanical deflection)

---

## ⚙️ Drivetrain: 12V DC Motor & Differential Gearing

### Drive System Selection:
The car is powered by a **12V DC brushed motor** driving the rear axle. This motor provides the high starting torque required to accelerate the car quickly from a complete stop.

### The Mechanical Differential:
A key mechanical feature of the drivetrain is the **rear differential gear system**. 
- **The Problem**: During a turn, the wheel on the outside of the turn has to travel a longer distance than the wheel on the inside of the turn.
- **The Solution**: Without a differential (a solid axle), both wheels would spin at the same speed, forcing one tire to slip. This would cause the car to fishtail and understeer. The mechanical differential allows the rear wheels to rotate at different speeds during turns while still receiving power from the motor, ensuring high-speed stability and tight, clean cornering.
