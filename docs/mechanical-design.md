# Mechanical Design - WRO 2026 Future Engineers

This document details the mechanical design of our autonomous vehicle, explaining the engineering reasoning, mathematical calculations, and design tradeoffs behind our custom chassis footprint, steering geometry, and drivetrain selections.

---

## 🏎️ Chassis & Component Layout

Instead of using a pre-built commercial chassis, we designed and manufactured our own custom chassis. This allowed us to achieve complete design freedom, customize the placement of components, and optimize the overall footprint.

```
┌────────────────────────────────────────────────────────┐
│  Upper Tier: D500 LiDAR (360° view) & Camera Rev 1.3  │
├────────────────────────────────────────────────────────┤
│  Middle Tier: Raspberry Pi 4B & ESP32-S3 Dev Board     │
├────────────────────────────────────────────────────────┤
│  Lower Tier: 12V Motor, Differential, Converters, Batt │
└────────────────────────────────────────────────────────┘
```

![Kodama Trinus 3D Printer](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/media/robot-photos/kodama_trinus.jpeg)

### Vehicle Dimensions & Prototyping Constraints:
- **Footprint**: **$24 \times 12\text{ cm}$**. This footprint was selected to accommodate the Raspberry Pi 4B, ESP32-S3, and sensors while maintaining high agility and clean movement ranges on the track.
- **Manufacturing Constraints (3D Printer)**: The chassis was printed on a **Kodama Trinus 3D printer** using **PLA (Polylactic Acid)**. Because the printer's bed size is quite small (**$12 \times 12\text{ cm}$**), we designed the main chassis to be printed in **two halves** that are securely bolted together. This modular design enabled high-accuracy prints without requiring a large-format industrial printer.
- **Center of Gravity**: Heavy components (such as the 2P3S Samsung battery pack, the heavy 37mm DC drive motor, and the dual metal buck converters) are mounted as low as possible on the lower tier. This prevents the vehicle from tipping or rolling during high-speed, sharp evasive maneuvers around obstacles.

---

## 🔧 Steering Mechanism: Ackermann Geometry

Our steering utilizes a highly reliable **Ackermann steering mechanism** to control the front wheels.

![Ackermann Steering CAD Render](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/cad/renders/ackermann_cad.png)

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

## ⚙️ Drivetrain: Gearing, Speed/Torque Formulas, & Differential

The drivetrain relies on a rear-wheel-drive system driven by a powerful motor and managed by a custom differential.

### 1. Speed & Velocity Calculations:
- **Motor Specifications**: 37mm DC gearmotor delivering **$333\text{ RPM}$** ($5.55\text{ rev/s}$) at max speed under load.
- **Wheel Diameter**: $D = 65\text{ mm} = 0.065\text{ m}$.
- **Wheel Circumference**: 

  $$C = \pi \cdot D = \pi \cdot 0.065\text{ m} \approx 0.2042\text{ meters per revolution}$$

- **Maximum Theoretical Linear Velocity ($v_{\text{max}}$)**:

  $$v_{\text{max}} = \text{Rotational Speed (rev/s)} \cdot C = 5.55\text{ rev/s} \cdot 0.2042\text{ m} \approx 1.13\text{ m/s} \quad (4.07\text{ km/h})$$

- **Reasoning**: A top velocity of $\sim 1.13\text{ m/s}$ provides the perfect balance between fast lap times and controlled stopping distance on the WRO track, allowing the camera and Lidar perception loops to react comfortably before approaching walls or obstacles.

### 2. Torque & Acceleration Reasoning:
- The 37mm gearmotor's internal gearbox provides high stall torque ($\approx 3.5\text{ kg}\cdot\text{cm}$), ensuring that the car can accelerate smoothly from a complete stop even under the weight of the heavy 2P3S Samsung battery pack ($1.2\text{ kg}$ total vehicle mass).

### 3. Transmission & Belt Tensioner:
- Power is transferred from the motor to the differential gearbox via a **drive belt**. A custom **belt tensioner** keeps the belt tight to prevent slippage during rapid acceleration and braking.

### 4. The Mechanical Differential:
When the car turns, the outer wheel must travel a longer path than the inner wheel. If both wheels spun at the same speed (solid axle), the wheels would skid, causing severe understeer and tire wear.
- **Custom Build**: We designed and manufactured a custom differential gearbox housing using **nylon plastic gears taken from toys** mounted on high-speed ball bearings.
- **Function**: This differential system successfully prevents rear-wheel skidding, allowing the car to make smooth, clean cornering maneuvers at high speed.

![Differential Gear Housing CAD](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/cad/renders/differential_cad.jpeg)
![Full Drivetrain Assembly with Belt Tensioner](file:///C:/Users/basha/OneDrive/Desktop/Studies/External/WRO%20Competition/wro2026/media/robot-photos/drivetrain_physical.jpeg)
