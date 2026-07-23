/*
  esp32_firmware.ino
  WRO 2026 Self-Driving Car - ESP32-S3 Actuator Controller
  
  Protocol format from Raspberry Pi: "S<angle>,<speed>\n"
  Example: "S86,150\n"  (Angle: 0..180, Speed: -255..255)
  
  Hardware Pinout:
    - Motor Driver Input 1 (AIN1) -> ESP32 GPIO 16
    - Motor Driver Input 2 (AIN2) -> ESP32 GPIO 17
    - Motor Encoder Phase C1      -> ESP32 GPIO 32
    - Motor Encoder Phase C2      -> ESP32 GPIO 33
    - Steering Servo (MG996R)     -> ESP32 GPIO 18
    - UART Interface to Pi:
        ESP32 RX -> GPIO 4 (Connects to Raspberry Pi TX / GPIO 14)
        ESP32 TX -> GPIO 5 (Connects to Raspberry Pi RX / GPIO 15)
        
  Required Arduino Libraries:
    - ESP32Servo (Install via Arduino Library Manager)
*/

#include <ESP32Servo.h>

// --- PIN CONFIGURATION ---
#define MOTOR_AIN1_PIN 16  // Motor Driver Control Input 1
#define MOTOR_AIN2_PIN 17  // Motor Driver Control Input 2
#define ENCODER_C1_PIN 32  // Motor Encoder Signal 1
#define ENCODER_C2_PIN 33  // Motor Encoder Signal 2
#define SERVO_PIN      18  // Steering Servo PWM pin

// --- GPIO UART CONFIGURATION ---
#define USE_GPIO_UART  true
#define UART_RX_PIN    4   // ESP32 RX Pin (Connects to Raspberry Pi TX / GPIO 14)
#define UART_TX_PIN    5   // ESP32 TX Pin (Connects to Raspberry Pi RX / GPIO 15)
#define UART_BAUD      115200

// --- SAFETY WATCHDOG ---
#define WATCHDOG_TIMEOUT_MS 500  // Stop motor if Pi loses connection for > 500ms

// --- GLOBAL OBJECTS & STATE ---
Servo steeringServo;
unsigned long lastPacketTime = 0;
volatile long encoderTicks = 0;

int currentAngle = 90; // Default straight
int currentSpeed = 0;  // Default stopped

// --- ENCODER INTERRUPT SERVICE ROUTINE ---
void IRAM_ATTR handleEncoderInterrupt() {
  if (digitalRead(ENCODER_C2_PIN) == HIGH) {
    encoderTicks++;
  } else {
    encoderTicks--;
  }
}

void setup() {
  // 1. Initialize USB Serial (ESP32-S3 Native USB-CDC for debugging)
  Serial.begin(UART_BAUD);

  // 2. Initialize GPIO Hardware UART (Serial1) for Raspberry Pi link
#if USE_GPIO_UART
  Serial1.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
#endif

  // 3. Attach Steering Servo
  ESP32PWM::allocateTimer(0);
  steeringServo.setPeriodHertz(50);            // Standard 50Hz servo frequency
  steeringServo.attach(SERVO_PIN, 500, 2500);  // 0.5ms - 2.5ms pulse width bounds
  steeringServo.write(currentAngle);

  // 4. Initialize Motor & Encoder Pins
  pinMode(MOTOR_AIN1_PIN, OUTPUT);
  pinMode(MOTOR_AIN2_PIN, OUTPUT);
  pinMode(ENCODER_C1_PIN, INPUT_PULLUP);
  pinMode(ENCODER_C2_PIN, INPUT_PULLUP);

  // Attach Interrupt to Encoder Channel 1
  attachInterrupt(digitalPinToInterrupt(ENCODER_C1_PIN), handleEncoderInterrupt, RISING);

  stopMotor();
  lastPacketTime = millis();
}

void loop() {
  // 1. Check for commands over GPIO Hardware UART (Serial1)
#if USE_GPIO_UART
  if (Serial1.available() > 0) {
    String line = Serial1.readStringUntil('\n');
    parseCommand(line);
  }
#endif

  // 2. Check for commands over USB Serial (Backup / Debugging)
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    parseCommand(line);
  }

  // 3. Safety Watchdog Trigger
  if (millis() - lastPacketTime > WATCHDOG_TIMEOUT_MS) {
    stopMotor();
  }
}

void parseCommand(String line) {
  line.trim();
  if (line.startsWith("S")) {
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
