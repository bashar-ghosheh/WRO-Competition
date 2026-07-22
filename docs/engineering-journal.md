# Engineering Journal - WRO 2026 Future Engineers

A log of testing runs, challenges faced, resolutions, and structural updates during development.

## 📅 Log Entry: July 22, 2026
### Reorganization & Field Prep
- Reorganized codebase into clean directories (`vision/`, `lidar/`, `control/`, `calibration/`, `firmware/`).
- Verified code cross-compatibility on the Pi.
- Configured camera slice (y = 190 to 250) and implemented 180° rotation (`FLIP_MODE = -1`) to support backwards mounting.
- Set safety bounds for the MG996R servo (steering center at 90, limits at 60 and 120).
- Created a headless Lidar web server plotter running on port 8001.
- Created an ESP32 C++ web-server steering calibration sketch.
