from deepface import DeepFace
import cv2
import serial
import time
import serial.tools.list_ports
from collections import deque

class LaserFaceTracker:
    def __init__(self, arduino_port=None, baud_rate=9600):
        self.cap = cv2.VideoCapture(0)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Arduino connection
        self.arduino = None
        self.laser_enabled = False
        if arduino_port:
            self.connect_to_arduino(arduino_port, baud_rate)
        
        # Camera properties
        self.camera_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.camera_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Tracking history for smoothing
        self.history = []
        self.history_size = 5
        
    def connect_to_arduino(self, port, baud_rate=9600):
        """
        Establish connection with Arduino
        """
        try:
            self.arduino = serial.Serial(port, baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"Connected to Arduino on {port}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to Arduino: {e}")
            return False
    
    def send_coordinates(self, x, y):
        """
        Send coordinates to Arduino with smoothing
        """
        if self.arduino and self.arduino.is_open:
            # Add to history for smoothing
            self.history.append((x, y))
            if len(self.history) > self.history_size:
                self.history.pop(0)
            
            # Calculate smoothed coordinates
            smooth_x = sum([pos[0] for pos in self.history]) / len(self.history)
            smooth_y = sum([pos[1] for pos in self.history]) / len(self.history)
            
            message = f"X{int(smooth_x):03d}Y{int(smooth_y):03d}\n"
            self.arduino.write(message.encode())

            print(smooth_x, smooth_y) # Debugging purposes
            
    def toggle_laser(self, enabled):
        """
        Toggle laser on/off
        """
        if self.arduino and self.arduino.is_open:
            command = "LASER1\n" if enabled else "LASER0\n"
            self.arduino.write(command.encode())
            self.laser_enabled = enabled
            print(f"Laser {'enabled' if enabled else 'disabled'}")
    
    def find_arduino_port(self):
        """
        Try to automatically find Arduino port
        """
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "Arduino" in port.description or "CH340" in port.description:
                return port.device
        return None
    
    def emotion(self, target_emotion="sad"):
        """
        We keep running this until the person shows the target emotion
        """
    
        sliding_window = deque(maxlen=50)
        

        for i in range(50):
            if i%7!=0:
                sliding_window.append(0)
            else:
                sliding_window.append(1)
        while True:
            ret, frame = self.cap.read()

            result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
            emotion = result[0]['dominant_emotion']

            # Draw the emotion text on the frame
            cv2.putText(frame, emotion, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Live Emotion Detection", frame)

            sliding_window.popleft()

            if emotion == target_emotion:
                sliding_window.append(1)
            else:
                sliding_window.append(0)
            
            if sum(sliding_window) >= 25: # I know im hard coding 50 and 25 but eh
                return True
            if cv2.waitKey(1) & 0xFF == ord('q'): # If we press q we quit
                break
        return False
    
    def detect_face_center(self):
        """
        Detect face and return center coordinates in terms of percent
        """
        ret, frame = self.cap.read()
        if not ret:
            return None, None, frame
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Get the largest face
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            
            # Calculate center
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Normalize coordinates (0-100 range)
            norm_x = int((center_x / self.camera_width) * 100)
            norm_y = int((center_y / self.camera_height) * 100)
            
            # Draw visualization
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"X: {norm_x}, Y: {norm_y}", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, f"Laser: {'ON' if self.laser_enabled else 'OFF'}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            return norm_x, norm_y, frame
        
        return None, None, frame
    
    def run(self):
        """
        Main tracking loop
        """
        print("Starting laser face tracking. Press 'q' to quit, 'l' to toggle laser.")
        
        self.emotion()


        while True:
            x, y, frame = self.detect_face_center()
            
            if x is not None and y is not None:
                # Send coordinates to Arduino
                self.send_coordinates(x, y)
            else:
                # No face detected, clear history
                self.history = []
            
            cv2.imshow('Laser Face Tracking', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('t'): # Toggle laser
                self.toggle_laser(not self.laser_enabled)
            elif key == ord(' '):  # Center laser
                self.send_coordinates(50, 50)
        self.cleanup()
    
    def cleanup(self):
        """
        Release resources
        """
        # Ensure laser is turned off
        self.toggle_laser(False)
        
        self.cap.release()
        cv2.destroyAllWindows()
        if self.arduino:
            self.arduino.close()
        print("Resources released")

# Main execution
if __name__ == "__main__":
    tracker = LaserFaceTracker()
    arduino_port = tracker.find_arduino_port()
    
    if arduino_port:
        print(f"Found Arduino at: {arduino_port}")
        tracker.arduino = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)  # Wait for Arduino connection
    else:
        print("Arduino not found. Continuing without Arduino connection.")
    
    tracker.run()