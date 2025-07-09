import cv2
import dlib
import time
import numpy as np
from scipy.spatial import distance as dist
from imutils import face_utils
import pyttsx3
import csv
import os
from datetime import datetime
from twilio.rest import Client  # Twilio for SMS functionality

# Twilio credentials from your Twilio account
account_sid = 'ACbb5f8d41fd08f29ac9e102d0ae9d3e36'  # Replace with your Twilio Account SID
auth_token = 'f7f273b5495d593afe58e2f68df62518'    # Replace with your Twilio Auth Token

# Initialize the Twilio client
client = Client(account_sid, auth_token)

# Function to send SMS alert
def send_sms_alert(user_phone_number, message):
    try:
        message = client.messages.create(
            to=user_phone_number,        # Use the user's phone number here
            from_="+18159576352",        # Your Twilio phone number
            body= 'Fatigue Detected Take a break'               # The content of the message
        )
        print(f"SMS sent to {user_phone_number}")
    except Exception as e:
        print(f"Error in sending SMS: {e}")   
user_phone_number = input("Enter your phone number: ")
message = "This is a test alert from your Fatigue Monitoring System."
send_sms_alert(user_phone_number, message)


# Function to save logs to a shared CSV file
def save_log_to_csv(user_id, event_type, event_detail):
    log_filename = 'all_users_logs.csv'
    log_entry = {
        'id': user_id,
        'event_type': event_type,
        'event_detail': event_detail,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    file_exists = os.path.exists(log_filename)
    with open(log_filename, mode='a', newline='') as file:
        fieldnames = ['id', 'event_type', 'event_detail', 'timestamp']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(log_entry)

# Function to calculate Eye Aspect Ratio (EAR)
def calculate_EAR(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    EAR = (A + B) / (2.0 * C)
    return EAR

# Function to calculate Mouth Aspect Ratio (MAR)
def calculate_MAR(mouth):
    A = dist.euclidean(mouth[3], mouth[9])
    B = dist.euclidean(mouth[2], mouth[10])
    C = dist.euclidean(mouth[0], mouth[6])
    MAR = (A + B) / (2.0 * C)
    return MAR

# Function to calculate head tilt angle
def calculate_head_tilt(landmarks):
    nose_tip = np.array([landmarks.part(30).x, landmarks.part(30).y])
    left_eye = np.array([landmarks.part(36).x, landmarks.part(36).y])
    right_eye = np.array([landmarks.part(45).x, landmarks.part(45).y])

    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]
    angle = np.arctan2(dy, dx) * 180.0 / np.pi
    return angle

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Thresholds for detection
EAR_THRESHOLD = 0.25
CLOSED_FRAMES_THRESHOLD = 20
HEAD_TILT_THRESHOLD = 20.0  # Maximum allowed head tilt angle in degrees

# Initialize dlib face detector and predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

# Indices for facial landmarks
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
(mStart, mEnd) = face_utils.FACIAL_LANDMARKS_IDXS["mouth"]

# Prompt for user ID
logged_in_user_id = input("Enter your User ID: ")

# User phone number (you can input this dynamically or set it based on the user profile)
user_phone_number = input("Enter your phone number (with country code): ")

# Start video capture
cap = cv2.VideoCapture(0)
FRAME_COUNT = 0
start_time = None

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    for face in faces:
        shape = predictor(gray, face)
        shape_np = face_utils.shape_to_np(shape)

        leftEye = shape_np[lStart:lEnd]
        rightEye = shape_np[rStart:rEnd]
        mouth = shape_np[mStart:mEnd]

        # Calculate metrics
        leftEAR = calculate_EAR(leftEye)
        rightEAR = calculate_EAR(rightEye)
        avg_EAR = (leftEAR + rightEAR) / 2.0
        MAR = calculate_MAR(mouth)
        tilt_angle = calculate_head_tilt(shape)

        # Draw facial landmarks and rectangle
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        mouthHull = cv2.convexHull(mouth)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [mouthHull], -1, (0, 255, 0), 1)
        cv2.rectangle(frame, (face.left(), face.top()), 
                      (face.right(), face.bottom()), (255, 0, 0), 2)

        # Eye closure detection
        if avg_EAR < EAR_THRESHOLD:
            if start_time is None:
                start_time = time.time()
            FRAME_COUNT += 1
            elapsed_time = time.time() - start_time

            if FRAME_COUNT >= CLOSED_FRAMES_THRESHOLD:
                cv2.putText(frame, "EYES CLOSED", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                save_log_to_csv(logged_in_user_id, 'Eye Closure', f'Closed for {elapsed_time:.2f} seconds')
                engine.say("Wake up!")
                engine.runAndWait()

                # Send SMS alert when eyes are closed
                message = "Alert: Drowsiness detected! Please take a break."
                send_sms_alert(user_phone_number, message)  # Trigger SMS alert

        else:
            FRAME_COUNT = 0
            start_time = None

        # Head tilt detection
        if abs(tilt_angle) > HEAD_TILT_THRESHOLD:
            cv2.putText(frame, "HEAD TILT DETECTED!", (50, 350),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            save_log_to_csv(logged_in_user_id, 'Head Tilt', 'Tilt detected')

        # Mouth yawning detection
        if MAR > 0.6:
            cv2.putText(frame, "YAWNING DETECTED!", (50, 400),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            save_log_to_csv(logged_in_user_id, 'Yawning', 'Yawning detected')

    # Display the resulting frame
    cv2.imshow("Fatigue Monitoring System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
