/*
  esp32_firmware.ino
  WRO 2026 Self-Driving Car - ESP32-S3 Actuator Controller
  
  Protocol format from Raspberry Pi: "S<angle>,<speed>\n"
  Example: "S86,150\n"  (Angle: 0..180, Speed: -255..255)
  
  Hardware:
    - Steering Servo: Connected to SERVO_PIN (GPIO 18)
    - Motor Driver (DRV8833 Channel A):
        AIN1 -> GPIO 4
        AIN2 -> GPIO 5
        nSLEEP -> Tied to 3.3V (or GPIO 6)
        
  Required Arduino Libraries:
    - ESP32Servo (Install via Arduino Library Manager)
*/

#include <ESP32Servo.h>

// --- PIN CONFIGURATION ---
#define SERVO_PIN      18  // Servo PWM control pin
#define MOTOR_AIN1_PIN 4   // DRV8833 Channel A Input 1
#define MOTOR_AIN2_PIN 5   // DRV8833 Channel A Input 2

// --- SAFETY WATCHDOG ---
#define WATCHDOG_TIMEOUT_MS 500  // Stop motor if Pi loses connection for > 500ms

// --- GLOBAL OBJECTS & STATE ---
Servo steeringServo;
unsigned long lastPacketTime = 0;

int currentAngle = 86; // Default straight
int currentSpeed = 0;  // Default stopped

void setup() {
  // 1. Initialize USB Serial (ESP32-S3 Native USB-CDC)
  Serial.begin(115200);

  // 2. Attach Servo
  ESP32PWM::allocateTimer(0);
  steeringServo.setPeriodHertz(50);            // Standard 50Hz servo frequency
  steeringServo.attach(SERVO_PIN, 500, 2500);  // 0.5ms - 2.5ms pulse width bounds
  steeringServo.write(currentAngle);

  // 3. Initialize Motor Pins
  pinMode(MOTOR_AIN1_PIN, OUTPUT);
  pinMode(MOTOR_AIN2_PIN, OUTPUT);
  stopMotor();

  lastPacketTime = millis();
}

void loop() {
  // 1. Read & parse incoming USB Serial commands
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.startsWith("S")) {
      // Parse format: S<angle>,<speed>
      int commaIndex = line.indexOf(',');
      if (commaIndex > 1) {
        String angleStr = line.substring(1, commaIndex);
        String speedStr = line.substring(commaIndex + 1);

        int targetAngle = angleStr.toInt();
        int targetSpeed = speedStr.toInt();

        // Clamp values safely
        targetAngle = constrain(targetAngle, 0, 180);
        targetSpeed = constrain(targetSpeed, -255, 255);

        // Drive Actuators
        setSteering(targetAngle);
        setMotorSpeed(targetSpeed);

        lastPacketTime = millis(); // Reset safety watchdog
      }
    }
  }

  // 2. Safety Watchdog Trigger
  if (millis() - lastPacketTime > WATCHDOG_TIMEOUT_MS) {
    stopMotor();
  }
}

void setSteering(int angle) {
  currentAngle = angle;
  steeringServo.write(angle);
}

void setMotorSpeed(int speed) {
  currentSpeed = speed;

  if (speed > 0) {
    // Forward Motion (AIN1 = PWM, AIN2 = LOW)
    analogWrite(MOTOR_AIN1_PIN, speed);
    analogWrite(MOTOR_AIN2_PIN, 0);
  } else if (speed < 0) {
    // Reverse Motion (AIN1 = LOW, AIN2 = PWM)
    analogWrite(MOTOR_AIN1_PIN, 0);
    analogWrite(MOTOR_AIN2_PIN, abs(speed));
  } else {
    // Stop / Coast
    stopMotor();
  }
}

void stopMotor() {
  analogWrite(MOTOR_AIN1_PIN, 0);
  analogWrite(MOTOR_AIN2_PIN, 0);
}
