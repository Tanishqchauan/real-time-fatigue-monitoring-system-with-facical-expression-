# real-time-fatigue-monitoring-system-with-facical-expression-

A published research project that detects drowsiness and fatigue using facial expression analysis in real-time.

🚀 Overview
This system leverages computer vision and machine learning techniques to detect driver fatigue by analyzing eye closure, yawning, and head movements in real time. It triggers alerts (sound) and generates session reports to prevent accidents due to drowsiness.

This work Published as research paper based on the system in Springer LNNS (Vol. 1325), presented at ICAC 2024.

🛠️ Tools & Technologies
Python: OpenCV, dlib, numpy, scipy, time, winsound

Real-time detection using webcam feed

Facial landmarks detection (68 points model)

Alert system: sound + session reports

📌 Features
👀 Eye closure detection with EAR (Eye Aspect Ratio)

👄 Yawn detection using MAR (Mouth Aspect Ratio)

🕹️ Head movement detection (tilt, nod, down)

🔊 Alarm system when drowsiness detected

📊 Generates session report after every run



📦 How to Run
Clone this repo

Install dependencies:
pip install -r requirements.txt
python app.py
