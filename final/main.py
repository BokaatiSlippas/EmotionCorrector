from deepface import DeepFace
import cv2
from collections import deque
import numpy as np
import serial
import time
import math

class LaserFaceTracker:
    def __init__(self, arduino_port=None, baud_rate=9600, smoothing_window=5):
        self.cap = cv2.VideoCapture(0)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Camera properties
        self.camera_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.camera_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.smoothing_window = smoothing_window
        self.hor_angle_buffer = deque(maxlen=smoothing_window)
        self.vert_angle_buffer = deque(maxlen=smoothing_window)

        # Arduino connection
        self.arduino = None
        self.laser_enabled = False
        if arduino_port:
            self.connect_to_arduino(arduino_port, baud_rate)
        else:
            self.connect_to_arduino("COM5", baud_rate)
            return
        time.sleep(1)
        
    
    def connect_to_arduino(self, port, baud_rate=9600):
        """
        Establish connection with Arduino
        """
        try:
            self.arduino = serial.Serial(port, baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"Connected to Arduino on {port}")
            return True
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            return False
    
    def emotion(self, target_emotion="neutral"):
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
    
    def convertToAngles(self, x, y, CAMERA_HFOV=60, CAMERA_VFOV=45, LASER_HEIGHT_ABOVE_CAMERA=50):
        """
        Convert camera coordinates (0-100%) to angles for laser turret
        
        Args:
            x: Horizontal position (0-100%, 50 = center)
            y: Vertical position (0-100%, 50 = center)
        
        Returns:
            hor_angle, vert_angle: Angles in degrees for servo motors
        """
        # Typical webcam: 60-70 degrees horizontal, 45-50 degrees vertical
        # Distance between camera and laser in mm
        x_offset_percent = (x - 50) / 50.0  # -1.0 (left) to +1.0 (right)
        y_offset_percent = (y - 50) / 50.0  # -1.0 (top) to +1.0 (bottom)
        
        # Calculate angles from camera perspective
        # These are the angles from camera center to the target
        camera_hor_angle = x_offset_percent * (CAMERA_HFOV / 2.0)
        camera_vert_angle = y_offset_percent * (CAMERA_VFOV / 2.0)
        
        # Convert camera angles to laser angles
        # Laser is above camera, so we need to account for parallax
        if LASER_HEIGHT_ABOVE_CAMERA > 0:
            # For horizontal (pan) - simpler, just use same angle
            laser_hor_angle = camera_hor_angle
            
            # For vertical (tilt) - more complex due to offset
            # We need to calculate the actual target distance
            # Assuming the target is at distance D from camera
            
            # Estimate target distance - you might need to calibrate this!
            # For face tracking, typical distance is 500-1000mm
            ESTIMATED_TARGET_DISTANCE = 500  # mm
            
            # Calculate vertical offset caused by laser-camera separation
            vertical_offset_angle = math.degrees(
                math.atan(LASER_HEIGHT_ABOVE_CAMERA / ESTIMATED_TARGET_DISTANCE)
            )
            
            # Adjust tilt angle based on geometry
            # The laser needs to point slightly lower than the camera
            laser_vert_angle = camera_vert_angle - vertical_offset_angle
        else:
            # If laser is at same height as camera (no parallax)
            laser_hor_angle = camera_hor_angle
            laser_vert_angle = camera_vert_angle
        
        return laser_hor_angle, laser_vert_angle

    def smooth_angles(self, hor_angle, vert_angle):
        """
        Simple sliding window smoothing
        Returns smoothed angles
        """
        # Add current angles to buffers
        self.hor_angle_buffer.append(hor_angle)
        self.vert_angle_buffer.append(vert_angle)
        
        # Calculate average if buffer has values
        if len(self.hor_angle_buffer) == 5:
            smooth_hor = sum(self.hor_angle_buffer) / len(self.hor_angle_buffer)
            smooth_vert = sum(self.vert_angle_buffer) / len(self.vert_angle_buffer)
            return smooth_hor, smooth_vert
        return hor_angle, vert_angle # only for the starting values

    def run(self):
        """
        Main tracking loop
        """
        print("Starting laser face tracking. Press 'q' to quit.")
        
        self.emotion()

        if not self.emotion():
            return
        while True:
            x, y, frame = self.detect_face_center() # x,y axis values
            if x is not None and y is not None:
                horAngle, vertAngle = self.convertToAngles(x, y)
                
                if horAngle is not None and vertAngle is not None:
                    smooth_hor, smooth_vert = self.smooth_angles(horAngle, vertAngle)
                    # Send coordinates to Arduino
                    self.send_coordinates(smooth_hor, smooth_vert)
                    cv2.imshow('Laser Face Tracking', frame)
                  
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        self.cleanup()

    def send_coordinates(self, horAngle, vertAngle):
        message = f"H{int(horAngle):03d}V{int(vertAngle):03d}\n"
        print(message)
        try:
            self.arduino.write(message.encode())
        except Exception as e:
            print(f"Failed to send to Arduino: {e}")


if __name__ == "__main__":
    laser_face_tracker = LaserFaceTracker()
    laser_face_tracker.run()