# Mechanical Design - WRO 2026 Future Engineers

This document details the mechanical design of our autonomous vehicle, explaining the engineering reasoning behind our custom chassis footprint, steering geometry, and drivetrain selections.

---

## 🏎️ Chassis & Component Layout

Instead of using a pre-built commercial chassis, we designed and manufactured our own custom chassis. This allowed us to achieve complete design freedom, customize the placement of components, and optimize the overall footprint.

### Vehicle Dimensions & Prototyping Constraints:
- **Footprint**: **$24 \times 12\text{ cm}$**. This footprint was selected to accommodate the Raspberry Pi 4B, ESP32-S3, and sensors while maintaining high agility and clean movement ranges on the track.
- **Manufacturing Constraints (3D Printer)**: The chassis was printed on a **Kodama Trinus 3D printer** using **PLA (Polylactic Acid)**. Because the printer's bed size is quite small (**$12 \times 12\text{ cm}$**), we designed the main chassis to be printed in **two halves** that are securely bolted together. This modular design enabled high-accuracy prints without requiring a large-format industrial printer.
- **Center of Gravity**: Heavy components (such as the 2P3S Samsung battery pack, the heavy 37mm DC drive motor, and the dual metal buck converters) are mounted as low as possible on the lower tier. This prevents the vehicle from tipping or rolling during high-speed, sharp evasive maneuvers around obstacles.

---

## 🔧 Steering Mechanism: Ackermann Geometry

Our steering utilizes a highly reliable **Ackermann steering mechanism** to control the front wheels. 

```
   [Inside Wheel: turns sharper]             [Outside Wheel: turns wider]
             \                                      /
              \----[Knuckle with Bearings]---------/
                    \                              /
                     \----[Ackermann Cross-Link]--/
                                    |
                            [Main Link Arm]
                                    |
                           [MG996R Servo Motor]
```

### Ackermann Design & Linkages:
- **Simple Linkage**: We chose a straightforward cross-link between the Ackermann arms of both front wheel knuckles, with an additional link arm connecting the servo horn to the main link.
- **Low Friction Connections**: All joints and pivot points in the steering system are secured with **M2 screws**, which provide low mechanical resistance and minimize steering backlash.
- **Front Wheel Knuckles**: To ensure the front steering wheels spin frictionlessly, we designed custom knuckles consisting of a small axle, a main plate, and **dual ball bearings** mounted inside the wheel assembly. The knuckle plates feature two arms: one for the Ackermann linkage and another revolving around the chassis arm.
- **Actuator Selection & Calibration**:
  - **MG996R Servo**: A high-torque metal-gear servo was selected. Standard plastic/nylon gear servos quickly strip their gears under the high lateral forces of steering at speed.
  - **Software Bounds Mapping**: To prevent the servo from forcing the wheels past their mechanical limits (which would stall the motor and burn out the servo controller), the software enforces strict boundaries:
    - **Neutral Center**: `90`
    - **Max Left Steering**: `60` (30° mechanical deflection)
    - **Max Right Steering**: `120` (30° mechanical deflection)

---

## ⚙️ Drivetrain: Gearing & Mechanical Differential

The drivetrain relies on a rear-wheel-drive system driven by a powerful motor and managed by a custom differential.

### Drive Motor & Belt Drive:
- **Motor**: A high-torque **37mm DC gearmotor** paired with a powerful gearbox. This motor delivers **333 RPM** at maximum speed, providing a wide range of speeds, a high torque ceiling, and tight control for precise movements.
- **Transmission**: The motor transfers power to the rear differential gearbox via a **drive belt**. A custom **belt tensioner** keeps the belt tight to prevent slippage during rapid acceleration and braking.

### The Mechanical Differential:
When the car turns, the outer wheel must travel a longer path than the inner wheel. If both wheels spun at the same speed (solid axle), the wheels would skid, causing severe understeer and tire wear.
- **Custom Build**: We designed and manufactured a custom differential gearbox housing using **nylon plastic gears taken from toys** mounted on high-speed ball bearings.
- **Function**: This differential system successfully prevents rear-wheel skidding, allowing the car to make smooth, clean cornering maneuvers at high speed.

