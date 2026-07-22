/*
  servo_web_calibration.ino
  WRO 2026 - ESP32-S3 Wi-Fi Web Server Steering Calibrator (C++)
  
  Creates a standalone Wi-Fi Access Point directly on the ESP32.
  Connect your laptop or phone directly to the ESP32's Wi-Fi network:
    SSID: ESP32-Servo-Calibrator
    Password: password123
    
  Then open your browser and go to:
    http://192.168.4.1
    
  Use this live web interface to calibrate your MG996R servo limits!
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

#define SERVO_PIN 18

Servo steeringServo;
WebServer server(80);

// SSID and Password for the ESP32 Access Point
const char *ssid = "ESP32-Servo-Calibrator";
const char *password = "password123";

int currentAngle = 90; // Default center position

// HTML/JS code for the web page, stored in flash memory (PROGMEM)
const char HTML_CONTENT[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Steering Calibrator</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #121216;
            color: #ffffff;
            text-align: center;
            padding: 20px;
            margin: 0;
        }
        .card {
            background: #1e1e24;
            max-width: 450px;
            margin: 40px auto;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        h1 { color: #00ff88; margin-bottom: 5px; }
        .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }
        .display { font-size: 72px; font-weight: bold; color: #00ddff; margin: 20px 0; }
        input[type=range] { width: 100%; margin: 25px 0; accent-color: #00ff88; }
        .btn-group { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        button {
            background: #333344;
            border: none;
            color: white;
            padding: 12px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.1s;
        }
        button:hover { background: #444455; }
        .presets { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 15px; }
        .presets button { background: #0088cc; }
        .presets button:hover { background: #00aaff; }
    </style>
</head>
<body>
    <div class="card">
        <h1>ESP32 Steering</h1>
        <div class="subtitle">C++ Web Server Servo Calibrator</div>
        <div class="display"><span id="angle-val">90</span>&deg;</div>
        
        <input type="range" id="slider" min="0" max="180" value="90" oninput="sendAngle(this.value)" />
        
        <div class="btn-group">
            <button onclick="adjust(-5)">-5&deg;</button>
            <button onclick="adjust(-1)">-1&deg;</button>
            <button onclick="adjust(1)">+1&deg;</button>
            <button onclick="adjust(5)">+5&deg;</button>
        </div>
        
        <div class="presets">
            <button onclick="sendAngle(60)">LEFT (60&deg;)</button>
            <button onclick="sendAngle(90)" style="background:#00ff88; color:#121212;">CENTER (90&deg;)</button>
            <button onclick="sendAngle(120)">RIGHT (120&deg;)</button>
        </div>
    </div>

    <script>
        const slider = document.getElementById('slider');
        const display = document.getElementById('angle-val');
        let throttleTimer;

        function sendAngle(val) {
            display.innerText = val;
            slider.value = val;
            
            // Throttle requests slightly so we don't flood the ESP32 server during dragging
            clearTimeout(throttleTimer);
            throttleTimer = setTimeout(() => {
                fetch('/steer?angle=' + val);
            }, 30);
        }

        function adjust(diff) {
            let newVal = parseInt(slider.value) + diff;
            newVal = Math.max(0, Math.min(180, newVal));
            sendAngle(newVal);
        }
    </script>
</body>
</html>
)rawliteral";

// Handler for "/" route (Sends the HTML page)
void handleRoot() {
  server.send_P(200, "text/html", HTML_CONTENT);
}

// Handler for "/steer?angle=XX" route (Moves the servo)
void handleSteer() {
  if (server.hasArg("angle")) {
    int angle = server.arg("angle").toInt();
    angle = constrain(angle, 0, 180);
    
    currentAngle = angle;
    steeringServo.write(currentAngle);
    
    Serial.print("Steered to: ");
    Serial.println(currentAngle);
    
    server.send(200, "text/plain", "OK");
  } else {
    server.send(400, "text/plain", "Bad Request");
  }
}

void setup() {
  Serial.begin(115200);
  
  // Attach Steering Servo
  ESP32PWM::allocateTimer(0);
  steeringServo.setPeriodHertz(50);
  steeringServo.attach(SERVO_PIN, 500, 2500);
  steeringServo.write(currentAngle);

  // Set up ESP32 Wi-Fi Access Point (AP Mode)
  Serial.println("Starting Access Point...");
  WiFi.softAP(ssid, password);
  
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP IP Address: ");
  Serial.println(myIP);

  // Define server routes
  server.on("/", handleRoot);
  server.on("/steer", handleSteer);
  
  // Start server
  server.begin();
  Serial.println("C++ HTTP Web Server started.");
}

void loop() {
  server.handleClient();
}
