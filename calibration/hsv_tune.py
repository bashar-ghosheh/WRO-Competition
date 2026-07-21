"""
hsv_tune.py

Standalone HSV threshold tuning tool for tuning red/green pillar detection.
Displays live video with trackbars to find optimal HSV min/max ranges.

Usage:
    python calibration/hsv_tune.py
"""

import cv2
import numpy as np

def nothing(x):
    pass

def main():
    window_name = "HSV Calibration Tool"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Create trackbars for color thresholding
    cv2.createTrackbar("H Min", window_name, 0, 180, nothing)
    cv2.createTrackbar("H Max", window_name, 180, 180, nothing)
    cv2.createTrackbar("S Min", window_name, 100, 255, nothing)
    cv2.createTrackbar("S Max", window_name, 255, 255, nothing)
    cv2.createTrackbar("V Min", window_name, 70, 255, nothing)
    cv2.createTrackbar("V Max", window_name, 255, 255, nothing)

    # Try initializing camera (Raspberry Pi Camera or standard USB webcam)
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        use_picam = True
        print("[INFO] Using Picamera2")
    except Exception as e:
        print(f"[WARN] Picamera2 unavailable ({e}), falling back to OpenCV VideoCapture(0)")
        cap = cv2.VideoCapture(0)
        use_picam = False

    try:
        while True:
            if use_picam:
                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] Failed to read frame from camera.")
                    break

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Get trackbar positions
            h_min = cv2.getTrackbarPos("H Min", window_name)
            h_max = cv2.getTrackbarPos("H Max", window_name)
            s_min = cv2.getTrackbarPos("S Min", window_name)
            s_max = cv2.getTrackbarPos("S Max", window_name)
            v_min = cv2.getTrackbarPos("V Min", window_name)
            v_max = cv2.getTrackbarPos("V Max", window_name)

            lower = np.array([h_min, s_min, v_min])
            upper = np.array([h_max, s_max, v_max])

            mask = cv2.inRange(hsv, lower, upper)
            result = cv2.bitwise_and(frame, frame, mask=mask)

            # Combine original and masked output side by side
            stacked = np.hstack((frame, result))
            cv2.imshow(window_name, stacked)

            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):  # ESC or 'q' to exit
                print(f"\n[TUNED VALUES] Lower: ({h_min}, {s_min}, {v_min}), Upper: ({h_max}, {s_max}, {v_max})")
                break
    finally:
        if use_picam:
            picam2.stop()
        else:
            cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
