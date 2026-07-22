/*
  servo_calibration.ino
  MG996R Servo Steering Calibration Sketch
  
  Upload this sketch to your ESP32-S3 from your laptop.
  Open the Arduino IDE Serial Monitor, set the baud rate to 115200, 
  and type any angle (0 to 180) to move the servo.
  
  Use this to find your exact steering bounds:
    - Neutral straight wheels (Center angle)
    - Maximum safe left angle (Before binding)
    - Maximum safe right angle (Before binding)
    
  Hardware:
    - Steering Servo: Connected to GPIO 18
*/

#include <ESP32Servo.h>

#define SERVO_PIN 18

Servo steeringServo;
int currentAngle = 90; // Default center

void setup() {
  // Initialize Serial Monitor at 115200 baud
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for USB serial connection to open
  }
  
  // Configure and attach the servo
  ESP32PWM::allocateTimer(0);
  steeringServo.setPeriodHertz(50);            // Standard 50Hz servo
  steeringServo.attach(SERVO_PIN, 500, 2500);  // 0.5ms - 2.5ms pulse widths
  steeringServo.write(currentAngle);
  
  Serial.println("=========================================");
  Serial.println("   MG996R Steering Calibration Sketch    ");
  Serial.println("=========================================");
  Serial.println("Type an angle (0-180) in the Serial Monitor");
  Serial.println("and press Enter to steer the wheels.");
  Serial.print("Current angle set to: ");
  Serial.print(currentAngle);
  Serial.println(" degrees.");
  Serial.println("-----------------------------------------");
}

void loop() {
  // Check if an angle has been typed in the Serial Monitor
  if (Serial.available() > 0) {
    // Read the typed integer
    int targetAngle = Serial.parseInt();
    
    // Clear any remaining characters (like newline '\n' or carriage return '\r')
    while (Serial.available() > 0) {
      Serial.read();
    }
    
    // Verify it is a valid servo angle
    if (targetAngle >= 0 && targetAngle <= 180) {
      currentAngle = targetAngle;
      steeringServo.write(currentAngle);
      
      Serial.print("-> Moving servo to: ");
      Serial.print(currentAngle);
      Serial.println(" degrees.");
    } else {
      Serial.println("[ERROR] Please type a valid angle between 0 and 180.");
    }
  }
}
