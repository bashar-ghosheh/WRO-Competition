# Engineering Journal - WRO 2026 Future Engineers

This journal logs our development milestones, the engineering challenges we faced, our testing attempts, the reasoning behind our design changes, and our system risk analysis.

---

## 🛡️ Risk Identification & Failure Mitigation Matrix

To ensure system reliability on race day, we identified potential hardware and software failure points and established mitigation strategies:

| Subsystem | Potential Failure / Risk | Severity / Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Power Distribution** | Voltage sag during motor acceleration causes Raspberry Pi brownout reset. | **HIGH** (Car stops running) | Powered Pi from a 12V-to-5V buck regulator backed by a high-capacity 2P3S Samsung 6Ah battery. |
| **Thermal Management** | BMS overheating melts PLA battery casing. | **HIGH** (Structural failure / fire hazard) | Repositioned BMS and installed a dedicated **5W active blower fan cooling rig**. |
| **Steering Linkage** | Servo forces wheels beyond physical limit, stripping gears. | **MEDIUM** (Mechanical breakdown) | Mechanically centered servo at 90° and clamped software bounds to 60° (left) and 120° (right). |
| **Communication** | USB Serial cable disconnects or drops packets due to EMI noise. | **HIGH** (Loss of control) | Implemented 500ms hardware watchdog in ESP32 firmware and auto-reconnect logic in Pi software. |
| **Computer Vision** | Ambient light reflections on track cause false positive pillar detections. | **MEDIUM** (Navigational error) | Cropped ROI to narrow 60px floor slice ($y=190$ to $250$), applied 180° rotation, and set min contour threshold to 50px. |
| **Lidar Sensing** | Black arena walls absorb laser light, causing zero-distance readings. | **HIGH** (Wall collision) | Replaced ToF sensors with D500 Lidar using true laser technology; added CRC8 data validation. |

---

## 📅 Log Entry 1: Sensor Suite Decisions
* **What we tried**: We initially planned to use a "trident" configuration of three VL53L1X Time-of-Flight (ToF) sensors (pointing left, front, and right) alongside the camera.
* **Why it didn't work**: Managing multiple ToF sensors on the Pi's I2C bus required configuring individual `XSHUT` pins to change their addresses dynamically on boot. This created significant wiring complexity, and the constant polling created high I2C bus latency. Furthermore, ToF sensors struggled to detect the black arena walls.
* **What we changed to**: We removed all ToF sensors from the design and relied strictly on the **D500 LiDAR** for all distance and wall-following perception.
* **Why**: The Lidar already provides a complete, high-resolution 360-degree polar distance map, which simplifies our cabling, reduces weight, and frees up Pi GPIO pins.

---

## 📅 Log Entry 2: Pi-to-ESP32 Communication Link
* **What we tried**: We originally wired the Raspberry Pi 4B directly to the ESP32-S3 RX/TX pins using the Pi's GPIO UART pins (`/dev/serial0`).
* **Why it didn't work**: The direct GPIO wiring was fragile and susceptible to electromagnetic interference (EMI) from the adjacent 12V motor cables. Additionally, because of chassis space constraints, accessing the Pi's physical GPIO header was difficult once mounted.
* **What we changed to**: We switched to a standard **USB-A to USB-C cable** linking the Pi's USB port to the ESP32-S3 Dev Board's native USB COM port.
* **Why**: The USB cable is shielded (reducing EMI noise) and provides a secure, hot-pluggable connection. If the cable is bumped loose mid-run, our updated `serial_link.py` code immediately detects the loss of port, triggers an emergency stop, and auto-reconnects when re-plugged.

---

## 📅 Log Entry 3: Camera Crop (ROI) & Orientation Tuning
* **What we tried**: We initially captured a full $640 \times 480$ camera frame and cropped it to a large vertical window from row `140` to `460`.
* **Why it didn't work**: The large window captured background objects off the track, reflections from the car's own front bumper, and ceiling lights, which caused false contour detections. It also took too long to process, reducing our frame rate.
* **What we changed to**: We set `ROI_TOP = 190` and `ROI_BOTTOM = 250` (a narrow 60-pixel vertical slice) and implemented a 180° rotation (`FLIP_MODE = -1`) because we mounted the camera backwards and upside-down.
* **Why**: This narrow slice isolates only the exact portion of the track floor where pillars appear before the car needs to steer. The reduced image size cut OpenCV processing time by over 60%, raising our frame rate to a stable 28+ FPS.

---

## 📅 Log Entry 4: Steering Linkage Protection
* **What we tried**: We ran our first steering tests using a full standard sweep of `50` (left) to `130` (right) centered at `86`.
* **Why it didn't work**: The MG996R is a very high-torque metal-gear servo. When commanded to steer to `50`, the Ackermann linkages physically hit the chassis frame. Because the servo kept drawing maximum current to reach `50`, it began heating up rapidly and threatened to strip the plastic linkages.
* **What we changed to**: We mechanically centered the servo horn at `90` (straight wheels) and enforced software constraints: `STEER_MAX_LEFT = 60` and `STEER_MAX_RIGHT = 120`.
* **Why**: This protects the MG996R from binding or stalling, ensuring electrical safety and mechanical longevity.

---

## 📅 Log Entry 5: A4950 Motor Driver Selection
* **What we tried**: We initially evaluated using standard low-power H-bridges (like the L298N module or the DRV8833).
* **Why it didn't work**: The L298N was physically too bulky for our $24 \times 12\text{ cm}$ footprint and suffered from high internal voltage drops. The DRV8833 had a safe operating limit of 10.8V, which would be overloaded by our fully charged 12V lithium-ion pack. Furthermore, the 37mm gearmotor can pull up to 2.5A at stall, which exceeds the continuous current rating of the DRV8833.
* **What we changed to**: We switched to the **A4950 motor driver IC**.
* **Why**: The A4950 is highly compact, has a wide input voltage range (up to 40V), and easily supports up to 3.5A peak output current, providing reliable control of the 37mm motor.

---

## 📅 Log Entry 6: BMS Heat Management & Active Cooling
* **What we tried**: We assembled our 12V 6Ah battery pack using Samsung cells with the BMS tucked inside the battery enclosure.
* **Why it didn't work**: Under load, the BMS got hot enough that it began melting through the plastic battery casing. Because our Kodama Trinus 3D printer can only print in PLA (which starts deforming at 60°C), we couldn't print a high-temperature chassis cover to resolve the heat issue.
* **What we changed to**: We repositioned the BMS away from the battery cells and built a custom **5W active blower fan cooling rig** to continuously blow cool air over the BMS heatsink.
* **Why**: This active cooling setup keeps the BMS operating at safe temperatures and prevents the PLA structural components from warping or smelling.

---

## 📅 Log Entry 7: Stacked Board Orientation
* **What we tried**: We initially laid out the Raspberry Pi 4B and the ESP32-S3 horizontally on the chassis floor.
* **Why it didn't work**: This layout consumed too much surface space on our compact $24 \times 12\text{ cm}$ chassis, leaving no room for the battery pack and drive motor, and restricted airflow around the processors.
* **What we changed to**: We designed a custom **stacked vertical mounting rack** for the boards.
* **Why**: While this layout made routing cable connections tighter and slightly more complex, it dramatically reduced the horizontal space consumed, preserved room for the drivetrain, and significantly improved passive air cooling.
