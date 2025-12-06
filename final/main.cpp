#include <Servo.h>

Servo horServo;
Servo vertServo;

const int relayPin = 2;
const int HOR_PIN = 6;
const int VERT_PIN = 7;

// Neutral/home position
const int HOR_HOME = 90;
const int VERT_HOME = 90;

int horPos = 90;
int vertPos = 90;

void setup() {
  Serial.begin(9600);
  
  // Set relay pins as OUTPUT
  pinMode(relayPin, OUTPUT);
  
  // Turn relays OFF initially
  digitalWrite(relayPin, LOW);  // Relay OFF
  
  horServo.attach(HOR_PIN);
  vertServo.attach(VERT_PIN);
  
  // Start at home position
  goHome();
  delay(1000);

  Serial.println("Setup finished");
}

void loop() {

  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');

    Serial.print("Received: ");
    Serial.println(data);
    
    // Parse "H123V045" format
    if (data.startsWith("H") && data.indexOf("V") > 0) {
      int hIndex = data.indexOf('H');
      int vIndex = data.indexOf('V');
      
      String horStr = data.substring(hIndex + 1, vIndex);
      String vertStr = data.substring(vIndex + 1);
      
      horPos = horStr.toInt();
      vertPos = vertStr.toInt();
      response(horPos, vertPos);
    }
  } else {
    goHome();
    Serial.println("No data received");
  }
}

void moveToAngles(int horAngle, int vertAngle) {
  // Move both servos simultaneously
  horServo.write(horAngle);
  vertServo.write(vertAngle);
}

void response(int horAngle, int vertAngle) {
  moveToAngles(horAngle, vertAngle);
  digitalWrite(relayPin, HIGH);   // Activate relay
  delay(200);                     // Wait 2 seconds
  // digitalWrite(relayPin1, LOW);    // Deactivate relay
}

void goHome() {
  moveToAngles(HOR_HOME, VERT_HOME);
  digitalWrite(relayPin, LOW);
  delay(200);
}
