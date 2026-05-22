# 🦺 Safety Lens - AI-Based PPE Monitoring System

## Project Description

**Safety Lens** is an advanced Personal Protective Equipment (PPE) monitoring system that uses artificial intelligence for real-time identification. The system is composed of two main modules working together:

1. **Main Application** (`#app-principal.py`): Responsible for real-time detection  
2. **Web Server** (`#servidor-web-site.py`): Web interface for visualization and data analysis

---

## 📁 Project Structure

```text
SafetyLens-main/
├── #app-principal.py              # Main detection application
├── #servidor-web-site.py          # Flask web server
├── #start-app-principal.bat       # Script to start the main app
├── #start-servidor-web-site.bat   # Script to start the web server
├── config.yaml                    # System configuration file
├── requirements.txt               # Project dependencies
├── database/
│   └── epi_detections.db          # SQLite database
├── model/
│   └── best.pt                    # Trained YOLO model
├── static/
│   └── style.css                  # Web interface styles
└── templates/
    └── index.html                 # Web page template
🚀 Features
1. PPE Detection (Main Application)
Real-time detection using YOLO v8
Identification of multiple PPE types:
Safety glasses
Helmet
Gloves
Ear protection
Tkinter graphical interface for configuration
Configurable visual and sound alert system
2. Web Interface (Web Server)
Real-time detection visualization
Date/time filtering
Statistical charts:
Distribution by PPE type
Detection timeline
Captured image visualization
Real-time updates via WebSocket
🗄️ Database

The system uses SQLite with the following structure:

Tables
1. epis
id (INTEGER PRIMARY KEY)
nome (TEXT NOT NULL UNIQUE)
2. detections
id (INTEGER PRIMARY KEY)
timestamp (TEXT NOT NULL)
frame_data (BLOB)
epi_id (INTEGER, FOREIGN KEY)
3. settings
id (INTEGER PRIMARY KEY)
camera_resolution_w (INTEGER)
camera_resolution_h (INTEGER)
brightness_value (INTEGER)
contrast_value (INTEGER)
sharpness_value (INTEGER)
grayscale_value (INTEGER)
min_confidence_value (REAL)
alert_frequency_value (INTEGER)
alert_duration_value (INTEGER)
delay_time_value (INTEGER)
selected_epi_classes (TEXT)
⚙️ Configuration (config.yaml)
alerts:
  delay_time: 10
  duration: 500
  frequency: 1000

camera:
  default_settings:
    brightness: 87
    contrast: 136
    grayscale: false
    sharpness: 1
  id: 0
  resolution:
    height: 720
    width: 1280

detection:
  classes:
    epi_ausentes:
      - 4  # Without safety glasses
      - 5  # Without helmet
      - 6  # Without gloves
      - 7  # Without ear protection

    epi_presentes:
      - 1  # With safety glasses
      - 2  # With helmet
      - 3  # With gloves

  min_confidence: 0.8

paths:
  database: database/epi_detections.db
  model: model/best.pt
💾 Installation
Clone the repository
Install the dependencies:
pip install -r requirements.txt
▶️ How to Run
1. Start the Main Application
#start-app-principal.bat

or

python #app-principal.py
2. Start the Web Server
#start-servidor-web-site.bat

or

python #servidor-web-site.py
3. Access the Web Interface
http://localhost:5000
📦 Main Dependencies
opencv-python
ultralytics (YOLO)
numpy
Pillow
flask
pyyaml
tkinter
💻 System Requirements
Python 3.8+
Webcam or USB camera
Windows (for sound alerts using winsound)
Recommended: 4GB+ RAM
📄 License

This project is licensed under the MIT License.
