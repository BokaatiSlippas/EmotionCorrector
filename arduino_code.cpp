#include <Servo.h>

// Servo objects
Servo panServo;
Servo tiltServo;

// Servo pins
const int panPin = 9;
const int tiltPin = 10;
const int laserPin = 11;

// Servo limits (adjust based on your mechanical setup)
const int panMin = 0;
const int panMax = 180;
const int tiltMin = 0;
const int tiltMax = 180;

// Current positions
int currentPan = 90;
int currentTilt = 90;

// Smoothing factors (0.0-1.0), lower = smoother but slower
float smoothingFactor = 0.2;

// Safety timeout (milliseconds)
unsigned long lastUpdateTime = 0;
const unsigned long safetyTimeout = 2000; // 2 seconds

void setup() {
  Serial.begin(9600);
  
  // Attach servos
  panServo.attach(panPin);
  tiltServo.attach(tiltPin);
  
  // Initialize laser pin
  pinMode(laserPin, OUTPUT);
  digitalWrite(laserPin, LOW); // Start with laser off
  
  // Center servos
  panServo.write(90);
  tiltServo.write(90);
  delay(1000); // Allow servos to reach position
  
  Serial.println("Arduino Laser Targeting System Ready");
}

void loop() {
  // Check for new coordinates from Python
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');
    data.trim();
    lastUpdateTime = millis(); // Reset safety timer
    
    // Parse coordinates in format: "X123Y456"
    if (data.startsWith("X") && data.indexOf("Y") != -1) {
      int xIndex = data.indexOf('X');
      int yIndex = data.indexOf('Y');
      
      String xStr = data.substring(xIndex + 1, yIndex);
      String yStr = data.substring(yIndex + 1);
      
      int x = xStr.toInt(); // 0-100
      int y = yStr.toInt(); // 0-100
      
      // Convert normalized coordinates to servo angles
      int targetPan = map(x, 0, 100, panMin, panMax);
      int targetTilt = map(y, 0, 100, tiltMin, tiltMax);
      
      // Smooth movement
      currentPan = smoothMove(currentPan, targetPan, smoothingFactor);
      currentTilt = smoothMove(currentTilt, targetTilt, smoothingFactor);
      
      // Move servos
      panServo.write(currentPan);
      tiltServo.write(currentTilt);
      
      // Turn on laser when target is acquired
      digitalWrite(laserPin, HIGH);
      
      // Optional: Send confirmation back to Python
      Serial.print("Targeting: Pan=");
      Serial.print(currentPan);
      Serial.print(", Tilt=");
      Serial.println(currentTilt);
    }
  }
  
  // Safety feature: Turn off laser if no updates received
  if (millis() - lastUpdateTime > safetyTimeout) {
    digitalWrite(laserPin, LOW);
    Serial.println("Safety timeout: Laser disabled");
    lastUpdateTime = millis(); // Prevent constant messaging
  }
  
  // Small delay to prevent overwhelming the Arduino
  delay(20);
}

// Smooth movement function
int smoothMove(int current, int target, float factor) {
  return current + factor * (target - current);
}