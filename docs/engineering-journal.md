# Engineering Journal - WRO 2026 Future Engineers

This journal logs our development milestones, the engineering challenges we faced, our testing attempts, and the reasoning behind our design changes.

---

## 📅 Log Entry 1: Sensor Suite Decisions
* **What we tried**: We initially planned to use a "trident" configuration of three VL53L1X Time-of-Flight (ToF) sensors (pointing left, front, and right) alongside the camera.
* **Why it didn't work**: Managing multiple ToF sensors on the Pi's I2C bus required configuring individual `XSHUT` pins to change their addresses dynamically on boot. This created significant wiring complexity, and the constant polling created high I2C bus latency. Furthermore, the distance data was redundant when combined with the Lidar.
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
* **Why**: This narrow slice isolates only the exact portion of the track floor where pillars appear before the car needs to steer. The reduced image size cut OpenCV processing time by over 60%, raising our frame rate to a stable 25+ FPS.

---

## 📅 Log Entry 4: Steering Linkage Protection
* **What we tried**: We ran our first steering tests using a full standard sweep of `50` (left) to `130` (right) centered at `86`.
* **Why it didn't work**: The MG996R is a very high-torque metal-gear servo. When commanded to steer to `50`, the Ackermann linkages physically hit the chassis frame. Because the servo kept drawing maximum current to reach `50`, it began heating up rapidly and threatened to strip the plastic linkages.
* **What we changed to**: We mechanically centered the servo horn at `90` (straight wheels) and enforced software constraints: `STEER_MAX_LEFT = 60` and `STEER_MAX_RIGHT = 120`.
* **Why**: This protects the MG996R from binding or stalling, ensuring electrical safety and mechanical longevity.
