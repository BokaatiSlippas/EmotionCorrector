#include <Servo.h>

Servo horServo;
Servo vertServo;

const int relayPin1 = 2;  // Connect to IN1
const int HOR_PIN = 6;
const int VERT_PIN = 7;

// Neutral/home position
const int HOR_HOME = 90;
const int VERT_HOME = 90;

// Example target positions
const int POSITION_1_HOR = 45;
const int POSITION_1_VERT = 60;

const int POSITION_2_HOR = 135;
const int POSITION_2_VERT = 30;

void setup() {
  Serial.begin(9600);
  
  // Set relay pins as OUTPUT
  pinMode(relayPin1, OUTPUT);
  
  // Turn relays OFF initially
  digitalWrite(relayPin1, LOW);  // Relay OFF

  
  horServo.attach(HOR_PIN);
  vertServo.attach(VERT_PIN);
  
  // Start at home position
  goHome();
  delay(5000);


  Serial.println("Setup finished");
}

void loop() {
  // Sequence 1
  response(POSITION_1_HOR, POSITION_1_VERT);
  goHome();
  delay(2000);
  
  // Sequence 2  
  response(POSITION_2_HOR, POSITION_2_VERT);
  goHome();
  delay(2000);
}

void moveToAngles(int horAngle, int vertAngle) {
  // Move both servos simultaneously
  horServo.write(horAngle);
  vertServo.write(vertAngle);
  delay(500); // Wait for movement
}

void goHome() {
  moveToAngles(HOR_HOME, VERT_HOME);
}

void response(int horAngle, int vertAngle) {
  moveToAngles(horAngle, vertAngle);
  digitalWrite(relayPin1, HIGH);   // Activate relay
  delay(2000);                     // Wait 2 seconds
  digitalWrite(relayPin1, LOW);    // Deactivate relay
}
