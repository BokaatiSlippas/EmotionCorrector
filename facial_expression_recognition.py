from deepface import DeepFace
import cv2
from collections import deque
import numpy as np

cap = cv2.VideoCapture(0)

def emotion(target_emotion="sad"):
    
    sliding_window = deque(maxlen=50)
    

    for i in range(50):
        if i%7!=0:
            sliding_window.append(0)
        else:
            sliding_window.append(1)
    while True:
        ret, frame = cap.read()

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
        if cv2.waitKey(1) & 0xFF == ord('f'): # If we press f we break
            break
    return False


def hone_in():
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        if len(faces)==1:
            x, y, w, h = faces[0]
            centre_x = x+w//2
            centre_y = y+h//2

            # Draw markers
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(frame, (centre_x, centre_y), 5, (0, 0, 255), -1)
            # Display coordinates
            cv2.putText(frame, f"Center: ({centre_x}, {centre_y})", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imshow("Face Centre Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('f'): # If we press f we break
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if emotion("happy"):
        hone_in()